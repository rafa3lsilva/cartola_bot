"""Monitoramento de alterações de última hora na escalação para o dashboard."""

from __future__ import annotations

import time

STATUS_LABELS = {
    2: "Dúvida",
    3: "Suspenso",
    5: "Contundido",
    6: "Nulo",
    7: "Provável",
}


def minutes_until_close(status_data: dict, now_ts: float | None = None) -> float | None:
    """Retorna minutos restantes para o fechamento do mercado, ou None se não aplicável."""
    if not status_data or status_data.get("status_mercado") != 1:
        return None
    fechamento = status_data.get("fechamento") or {}
    close_ts = fechamento.get("timestamp")
    if not close_ts:
        return None
    current_ts = now_ts if now_ts is not None else time.time()
    return round((float(close_ts) - current_ts) / 60.0, 1)


def check_lineup_risks(official_team: dict, mercado_data: dict) -> list[dict]:
    """
    Compara titulares e reservas do time com o status atual no mercado.
    Retorna lista de atletas que deixaram de estar 'Provável' (status_id != 7).
    """
    atletas_by_id = {
        int(a["atleta_id"]): a
        for a in mercado_data.get("atletas", [])
        if a.get("atleta_id") is not None
    }
    clubes = mercado_data.get("clubes", {})
    risks: list[dict] = []

    def _inspect_player(role: str, player: dict) -> None:
        raw_id = player.get("ID") or player.get("atleta_id")
        if raw_id is None:
            return
        a_id = int(raw_id)
        live_a = atletas_by_id.get(a_id)
        if not live_a:
            risks.append(
                {
                    "role": role,
                    "id": a_id,
                    "nome": player.get("Nome", f"ID {a_id}"),
                    "clube": player.get("Clube", ""),
                    "posicao": player.get("Posicao", ""),
                    "status_id": 6,
                    "status_nome": "Fora do mercado",
                }
            )
            return

        status_id = int(live_a.get("status_id", 6))
        if status_id != 7:
            c_id = str(live_a.get("clube_id", ""))
            clube_abrev = clubes.get(c_id, {}).get("abreviacao", player.get("Clube", ""))
            risks.append(
                {
                    "role": role,
                    "id": a_id,
                    "nome": live_a.get("apelido") or player.get("Nome", ""),
                    "clube": clube_abrev,
                    "posicao": player.get("Posicao", ""),
                    "status_id": status_id,
                    "status_nome": STATUS_LABELS.get(status_id, f"Status {status_id}"),
                }
            )

    for s in official_team.get("starters", []):
        _inspect_player("Titular", s)

    reservas = official_team.get("reserves") or {}
    if isinstance(reservas, dict):
        for pos, r in reservas.items():
            if isinstance(r, dict):
                r_copy = dict(r)
                r_copy.setdefault("Posicao", pos)
                _inspect_player("Reserva", r_copy)

    return risks
