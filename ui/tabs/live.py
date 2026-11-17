import pandas as pd
import streamlit as st

from cartola_bot.backtesting import save_round_snapshot
from cartola_bot.lineup_service import order_defensive_line
from ui.components import render_live_player_card


def render_live_tab(selected_df, reservas, capitao_nome, super_sub_pos_chosen, rodada_num, official_round, app_mode, api):
    # 🔴 PARCIAIS AO VIVO
    active_round = official_round if app_mode == "oficial" else rodada_num
    col_l1, col_l2 = st.columns([3, 1])
    with col_l1:
        st.subheader(f"🔴 Parciais em Tempo Real • M1TOS EC (Rodada {active_round})")
    with col_l2:
        st.button("🔄 Atualizar Parciais", use_container_width=True)

    try:
        pontuados_data = api.get_pontuados(active_round if active_round and active_round != '?' else None)
    except Exception:
        pontuados_data = api.get_pontuados()

    pontuados = pontuados_data.get('atletas', {})
    total_pontuados_count = len(pontuados)
    if total_pontuados_count > 0:
        save_round_snapshot(rodada=active_round, pontuados_data=pontuados_data)

    if total_pontuados_count == 0:
        st.info("ℹ️ Os jogos da rodada ainda não começaram ou os scouts ao vivo ainda não foram abertos pela Globo. Assim que os jogos começarem, as parciais aparecerão aqui automaticamente!")
    else:
        st.caption(f"📡 Dados ao vivo sincronizados com a Globo • {total_pontuados_count} atletas pontuaram na Rodada {active_round}.")

    # Calcular parciais do time e valorização
    live_rows = []
    total_live_pts = 0.0
    jogadores_jogando = 0
    valorizando_count = 0
    desvalorizando_count = 0

    # Mapear pontuações por posição para checagem do reserva de luxo
    pos_starter_scores = {'Goleiro': [], 'Lateral': [], 'Zagueiro': [], 'Meia': [], 'Atacante': []}

    for _, p in selected_df.iterrows():
        atleta_id_str = str(p.get('ID'))
        is_cap = (p['Nome'] == capitao_nome)
        preco_p = float(p.get('Preco', 10.0))
        min_val_p = float(p.get('Min_Val', preco_p * 0.37))

        if atleta_id_str in pontuados:
            pinfo = pontuados[atleta_id_str]
            pts_bruto = float(pinfo.get('pontuacao', 0.0))
            pts_calc = pts_bruto * 1.5 if is_cap else pts_bruto
            total_live_pts += pts_calc
            jogadores_jogando += 1
            status_live = f"🟢 {pts_bruto:.2f} pts"

            diff_v = pts_bruto - min_val_p
            if diff_v >= 0:
                val_str = f"📈 Valorizando (+{diff_v:.2f} pts | Mín: {min_val_p:.2f})"
                valorizando_count += 1
            else:
                val_str = f"📉 Desvalorizando (Faltam {abs(diff_v):.2f} pts | Mín: {min_val_p:.2f})"
                desvalorizando_count += 1

            scouts_raw = pinfo.get('scout', {})
            scouts_str = ", ".join([f"{k}:{v}" for k, v in scouts_raw.items()]) if scouts_raw else "Em campo"
        else:
            pts_bruto = None
            pts_calc = 0.0
            status_live = "⏳ Aguardando jogo"
            val_str = f"⏳ Mínimo: {min_val_p:.2f} pts"
            scouts_str = "-"

        if p['Posicao'] in pos_starter_scores:
            pos_starter_scores[p['Posicao']].append({
                'Nome': p['Nome'],
                'pts': pts_bruto,
                'jogou': (pts_bruto is not None)
            })

        nome_disp = f"👑 {p['Nome']} [C]" if is_cap else p['Nome']
        live_rows.append({
            "Posição": p['Posicao'],
            "Jogador": nome_disp,
            "Clube": p['Clube'],
            "Status / Pontos": status_live,
            "Pontos c/ Capitão": f"{pts_calc:.2f} pts" if pts_bruto is not None else "-",
            "Valorização / Mínimo": val_str,
            "Scouts na Partida": scouts_str
        })

    # Cards de Métricas Principais (Pontuação e Valorização)
    col_metric1, col_metric2 = st.columns(2)
    with col_metric1:
        st.html(f'''
        <div class="metric-card" style="background:linear-gradient(135deg, #1e3a8a, #0f172a); border:2px solid #38bdf8; min-height:105px; display:flex; flex-direction:column; justify-content:center; box-sizing:border-box;">
            <div class="metric-title" style="color:#38bdf8; font-size:0.75rem;">⚡ PONTUAÇÃO PARCIAL TOTAL</div>
            <div class="metric-value" style="font-size:1.9rem; color:#f8fafc; line-height:1.2;">{total_live_pts:.2f} <span style="font-size:1.0rem; color:#38bdf8;">pts</span></div>
            <div style="font-size:0.75rem; color:#94a3b8; margin-top:3px;">{jogadores_jogando} de 12 atletas em campo</div>
        </div>
        ''')
    with col_metric2:
        val_pill = f'<span style="color:#34d399;font-weight:800;">🟢 {valorizando_count}</span> <span style="color:#64748b;font-size:1.2rem;">/</span> <span style="color:#f87171;font-weight:800;">🔴 {desvalorizando_count}</span>' if jogadores_jogando > 0 else '<span style="color:#94a3b8;font-size:1.1rem;">Aguardando jogos</span>'
        st.html(f'''
        <div class="metric-card" style="background:linear-gradient(135deg, #064e3b, #0f172a); border:2px solid #34d399; min-height:105px; display:flex; flex-direction:column; justify-content:center; box-sizing:border-box;">
            <div class="metric-title" style="color:#34d399; font-size:0.75rem;">📈 VALORIZAÇÃO EM TEMPO REAL</div>
            <div class="metric-value" style="font-size:1.9rem; color:#f8fafc; line-height:1.2;">{val_pill}</div>
            <div style="font-size:0.75rem; color:#94a3b8; margin-top:3px;">Atletas acima / abaixo do mínimo</div>
        </div>
        ''')

    # Checagem ao vivo do Banco de Reservas (Regra Oficial do Cartola FC)
    # O reserva de uma posição só entra se um titular da mesma posição NÃO entrar em campo (0 minutos / não pontuou).
    best_res_pos = super_sub_pos_chosen
    if not best_res_pos and reservas:
        max_upside = -1.0
        for pos, r in reservas.items():
            up = r.get('Upside', r.get('Media_Ajustada', 0))
            if up > max_upside:
                max_upside = up
                best_res_pos = pos

    if best_res_pos and best_res_pos in reservas:
        super_res = reservas[best_res_pos]
        res_id_str = str(super_res.get('ID'))
        pts_res = float(pontuados[res_id_str].get('pontuacao', 0.0)) if res_id_str in pontuados else None
        titulares_pos = pos_starter_scores.get(best_res_pos, [])

        # Verificar se algum titular da posição não jogou ou se todos já atuaram
        titulares_sem_atuar = [t for t in titulares_pos if not t['jogou']]
        titulares_atuaram = [t for t in titulares_pos if t['jogou']]

        if total_pontuados_count == 0:
            st.info(f"🛡️ **Banco de Reservas Oficial ({super_res['Posicao']}):** **{super_res['Nome']}** ({super_res['Clube']}). Pela regra do Cartola FC, ele entrará caso algum titular da posição não atue.")
        elif titulares_sem_atuar and pts_res is not None:
            nom_sub = titulares_sem_atuar[0]['Nome']
            st.warning(f"🔄 **SUBSTITUIÇÃO EM POTENCIAL (Regra Oficial da Globo):** O titular **{nom_sub}** ainda não pontuou/não jogou. Se não atuar, **{super_res['Nome']} ({pts_res:.2f} pts)** entrará na pontuação oficial!")
        elif len(titulares_atuaram) == len(titulares_pos) and len(titulares_pos) > 0:
            pts_info = f"({pts_res:.2f} pts)" if pts_res is not None else "(não jogou)"
            st.success(f"✅ **Titulares de {best_res_pos} confirmados em campo!** Todos os titulares atuaram na rodada, portanto a pontuação deles é definitiva e o reserva {super_res['Nome']} {pts_info} não é acionado (Regra Oficial da Globo).")
        else:
            status_res_txt = f"já fez **{pts_res:.2f} pts**" if pts_res is not None else "ainda não jogou"
            st.info(f"⏳ **Reserva ({super_res['Posicao']}):** {super_res['Nome']} {status_res_txt}. Aguardando o término dos jogos para confirmação de presença de todos os titulares.")

    with st.expander("📊 Ver Tabela Detalhada de Parciais e Scouts", expanded=False):
        st.dataframe(pd.DataFrame(live_rows), use_container_width=True, hide_index=True)

    # ATAQUE AO VIVO
    atacantes = selected_df[selected_df['Posicao'] == 'Atacante']
    if not atacantes.empty:
        st.html('<div class="sector-header">⚡ ATAQUE AO VIVO</div>')
        cols_ata = st.columns(len(atacantes))
        for idx, (_, p) in enumerate(atacantes.iterrows()):
            with cols_ata[idx]:
                pinfo = pontuados.get(str(p.get('ID')))
                render_live_player_card(p, pinfo=pinfo, is_captain=(p['Nome'] == capitao_nome))

    # MEIO-CAMPO AO VIVO
    meias = selected_df[selected_df['Posicao'] == 'Meia']
    if not meias.empty:
        st.html('<div class="sector-header">🎯 MEIO-CAMPO AO VIVO</div>')
        cols_mei = st.columns(len(meias))
        for idx, (_, p) in enumerate(meias.iterrows()):
            with cols_mei[idx]:
                pinfo = pontuados.get(str(p.get('ID')))
                render_live_player_card(p, pinfo=pinfo, is_captain=(p['Nome'] == capitao_nome))

    # DEFESA AO VIVO (Laterais nas pontas, Zagueiros no centro)
    defesa_raw = selected_df[selected_df['Posicao'].isin(['Lateral', 'Zagueiro'])]
    if not defesa_raw.empty:
        defesa = order_defensive_line(defesa_raw)
        st.html('<div class="sector-header">🛡️ LINHA DEFENSIVA AO VIVO</div>')
        cols_def = st.columns(len(defesa))
        for idx, (_, p) in enumerate(defesa.iterrows()):
            with cols_def[idx]:
                pinfo = pontuados.get(str(p.get('ID')))
                render_live_player_card(p, pinfo=pinfo, is_captain=(p['Nome'] == capitao_nome))

    # GOLEIRO & TÉCNICO AO VIVO
    gol_tec = selected_df[selected_df['Posicao'].isin(['Goleiro', 'Técnico'])]
    if not gol_tec.empty:
        st.html('<div class="sector-header">🧤 GOLEIRO & COMANDO TÉCNICO AO VIVO</div>')
        cols_base = st.columns([1, 1, 1, 1])
        goleiro_df = selected_df[selected_df['Posicao'] == 'Goleiro']
        tecnico_df = selected_df[selected_df['Posicao'] == 'Técnico']

        with cols_base[1]:
            if not goleiro_df.empty:
                gp = goleiro_df.iloc[0]
                render_live_player_card(gp, pinfo=pontuados.get(str(gp.get('ID'))), is_captain=(gp['Nome'] == capitao_nome))
        with cols_base[2]:
            if not tecnico_df.empty:
                tp = tecnico_df.iloc[0]
                render_live_player_card(tp, pinfo=pontuados.get(str(tp.get('ID'))), is_captain=False)

    # BANCO DE RESERVAS AO VIVO
    if reservas:
        st.markdown("---")
        st.html('<div class="sector-header">🔄 BANCO DE RESERVAS AO VIVO</div>')
        res_cols = st.columns(len(reservas))
        for idx, (pos, r) in enumerate(reservas.items()):
            with res_cols[idx]:
                is_super = (pos == best_res_pos)
                rpinfo = pontuados.get(str(r.get('ID')))
                render_live_player_card(r, pinfo=rpinfo, is_super_sub=is_super)

    return pontuados, best_res_pos

