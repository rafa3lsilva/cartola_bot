"""Serviços de regras de escalação, ordenação tática e sincronização com a Globo."""

from __future__ import annotations

import pandas as pd

from cartola_bot.gsheets_manager import save_official_team

POS_ID_TO_NAME = {
    1: "Goleiro",
    2: "Lateral",
    3: "Zagueiro",
    4: "Meia",
    5: "Atacante",
}

POS_NAME_MAP = {
    "goleiro": "Goleiro",
    "lateral": "Lateral",
    "zagueiro": "Zagueiro",
    "meia": "Meia",
    "atacante": "Atacante",
    "gol": "Goleiro",
    "lat": "Lateral",
    "zag": "Zagueiro",
    "mei": "Meia",
    "ata": "Atacante",
}


def order_defensive_line(df_defesa: pd.DataFrame | None) -> pd.DataFrame | None:
    """Ordena a linha defensiva colocando os Laterais nas extremidades e os Zagueiros no centro."""
    if df_defesa is None or df_defesa.empty:
        return df_defesa

    lats = df_defesa[df_defesa["Posicao"] == "Lateral"]
    zags = df_defesa[df_defesa["Posicao"] == "Zagueiro"]

    if len(lats) >= 2:
        lat_left = lats.iloc[[0]]
        lat_right = lats.iloc[[1]]
        extra_lats = lats.iloc[2:] if len(lats) > 2 else pd.DataFrame()
        return pd.concat([lat_left, zags, extra_lats, lat_right])
    if len(lats) == 1:
        lat_left = lats.iloc[[0]]
        return pd.concat([lat_left, zags])
    return zags


def validate_lineup_rules(selected_df: pd.DataFrame | None, reservas: dict | None) -> tuple[bool, list[str]]:
    """Valida as regras oficiais do Cartola FC para titulares e banco de reservas."""
    errors: list[str] = []
    if selected_df is None or selected_df.empty:
        return False, ["Nenhum atleta titular selecionado."]

    if len(selected_df) < 12:
        errors.append(f"O time titular possui apenas {len(selected_df)} de 12 atletas necessários.")

    if reservas:
        for r_pos, r_obj in reservas.items():
            if not hasattr(r_obj, "get"):
                continue
            s_sub = selected_df[selected_df["Posicao"] == r_pos]
            if s_sub.empty:
                errors.append(
                    f"A posição **{r_pos}** não é utilizada nesta formação tática, portanto não pode conter reserva."
                )
                continue
            min_p = float(s_sub["Preco"].min())
            r_p = float(r_obj.get("Preco", 999.0))
            if r_p > min_p:
                errors.append(
                    f"O reserva **{r_obj.get('Nome')}** ({r_pos} - C$ {r_p:.2f}) custa mais que o titular mais barato "
                    f"da posição (C$ {min_p:.2f}). Regra oficial da Globo: o reserva deve custar no máximo o valor do titular mais barato."
                )
            status_id = r_obj.get("Status_ID")
            if status_id is not None and int(status_id) != 7:
                st_nome = r_obj.get("Status_Nome", "Não Provável")
                errors.append(
                    f"O reserva **{r_obj.get('Nome')}** ({r_pos}) possui status **'{st_nome}'**. "
                    "Apenas atletas com status **'Provável'** são permitidos."
                )

    return len(errors) == 0, errors


def parse_globo_team_payload(user_glb_team: dict) -> dict:
    """Extrai IDs de titulares, capitão, reserva de luxo e reservas do payload da API da Globo."""
    raw_atletas = user_glb_team.get("atletas", [])
    starters_ids: list[int] = []
    for a in raw_atletas:
        a_id = a.get("atleta_id", a.get("id")) if isinstance(a, dict) else a
        if a_id is not None:
            try:
                starters_ids.append(int(a_id))
            except (ValueError, TypeError):
                pass

    cap_id_raw = user_glb_team.get("capitao_id") or user_glb_team.get("capitao")
    cap_id = int(cap_id_raw) if cap_id_raw else None

    super_sub_id_raw = user_glb_team.get("reserva_luxo_id") or user_glb_team.get("reserva_luxo")
    super_sub_id = int(super_sub_id_raw) if super_sub_id_raw else None

    raw_reservas = user_glb_team.get("reservas", {})
    reserves_ids: dict[str, int] = {}

    if isinstance(raw_reservas, dict):
        for k, val in raw_reservas.items():
            try:
                pos_name = POS_ID_TO_NAME.get(int(k))
            except (ValueError, TypeError):
                pos_name = POS_NAME_MAP.get(str(k).lower().strip())

            if not pos_name and isinstance(val, dict) and "posicao_id" in val:
                pos_name = POS_ID_TO_NAME.get(int(val["posicao_id"]))

            r_id = None
            if isinstance(val, dict):
                r_id = val.get("atleta_id", val.get("id"))
            elif val is not None:
                try:
                    r_id = int(val)
                except (ValueError, TypeError):
                    pass

            if pos_name and r_id:
                reserves_ids[pos_name] = int(r_id)

    elif isinstance(raw_reservas, list):
        for item in raw_reservas:
            if isinstance(item, dict):
                p_id = item.get("posicao_id")
                pos_name = POS_ID_TO_NAME.get(int(p_id)) if p_id else None
                a_id = item.get("atleta_id", item.get("id"))
                if pos_name and a_id:
                    reserves_ids[pos_name] = int(a_id)

    return {
        "starters_ids": starters_ids,
        "cap_id": cap_id,
        "super_sub_id": super_sub_id,
        "reserves_ids": reserves_ids,
    }


def sync_team_from_globo(
    api,
    token: str,
    rodada_num: int | str,
    mercado_data: dict,
    partidas_data: dict,
    scorer,
) -> tuple[bool, str, dict]:
    """
    Busca a escalação mais recente da conta oficial do Cartola FC,
    processa titulares e reservas com os metadados do modelo
    e persiste como time oficial ativo (JSON local + Google Sheets).
    """
    if not token:
        return (
            False,
            "Token de autenticação não encontrado. Conecte sua conta Globo no menu lateral para sincronizar.",
            {},
        )

    try:
        user_glb_team = api.get_user_team(token)
    except Exception as e:
        return False, f"Falha ao conectar à API da Globo: {e}", {}

    if not user_glb_team:
        return (
            False,
            "Não foi possível obter a escalação da Globo. Verifique se seu token expirou ou renove a sessão.",
            {},
        )

    parsed = parse_globo_team_payload(user_glb_team)
    starters_ids = parsed["starters_ids"]
    cap_id = parsed["cap_id"]
    super_sub_id = parsed["super_sub_id"]
    reserves_ids = parsed["reserves_ids"]

    if not starters_ids:
        return False, "Nenhum atleta titular encontrado no time retornado pelo Cartola FC.", {}

    all_needed_ids = list(set(starters_ids + list(reserves_ids.values())))
    full_df = scorer.process_data(mercado_data, partidas_data, target_athlete_ids=all_needed_ids)

    starters_df = full_df[full_df["ID"].isin(starters_ids)].copy()

    if cap_id not in starters_df["ID"].tolist():
        if not starters_df.empty:
            cap_id = int(starters_df.sort_values(by="Media_Ajustada", ascending=False).iloc[0]["ID"])
        else:
            cap_id = starters_ids[0]

    starters_df["Is_Capitao"] = starters_df["ID"] == cap_id

    reserves_dict: dict = {}
    super_sub_pos = "Atacante"
    for pos, r_id in reserves_ids.items():
        sub_df = full_df[full_df["ID"] == r_id]
        if not sub_df.empty:
            r_series = sub_df.iloc[0].copy()
            starter_pos_players = starters_df[starters_df["Posicao"] == pos]
            worst_starter_xp = starter_pos_players["Media_Ajustada"].min() if not starter_pos_players.empty else 0.0
            r_series["Worst_Starter_XP"] = worst_starter_xp
            r_series["Expected_Gain"] = round(
                max(0.0, (r_series.get("Upside", r_series.get("Media_Ajustada", 0.0)) - worst_starter_xp) * 0.4), 2
            )
            reserves_dict[pos] = r_series
            if super_sub_id and int(r_id) == int(super_sub_id):
                super_sub_pos = pos

    if not super_sub_id or super_sub_pos not in reserves_dict:
        if "Atacante" in reserves_dict:
            super_sub_pos = "Atacante"
        elif "Meia" in reserves_dict:
            super_sub_pos = "Meia"
        elif reserves_dict:
            super_sub_pos = list(reserves_dict.keys())[0]

    actual_round = rodada_num
    if user_glb_team.get("rodada"):
        try:
            actual_round = int(user_glb_team["rodada"])
        except (ValueError, TypeError):
            pass
    elif actual_round == "?":
        actual_round = 31

    save_official_team(
        rodada=actual_round,
        starters_df=starters_df,
        captain_id=cap_id,
        reserves_dict=reserves_dict,
        super_sub_pos=super_sub_pos,
    )

    patrimonio_val = None
    glb_pat = (
        user_glb_team.get("patrimonio")
        or user_glb_team.get("time", {}).get("patrimonio")
        or user_glb_team.get("patrimonio_num")
    )
    if glb_pat is not None:
        try:
            patrimonio_val = float(glb_pat)
        except (ValueError, TypeError):
            pass

    return (
        True,
        f"Time da Rodada {actual_round} sincronizado com sucesso da Globo ({len(starters_df)} titulares e {len(reserves_dict)} reservas)!",
        {"patrimonio": patrimonio_val, "rodada": actual_round},
    )
