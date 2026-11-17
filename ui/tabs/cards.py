import time

import streamlit as st

from cartola_bot.gsheets_manager import save_official_team
from cartola_bot.lineup_service import order_defensive_line, validate_lineup_rules
from ui.components import handle_globo_escalacao_result, render_player_card
from ui.components import sync_team_from_globo_ui as sync_team_from_globo


def render_cards_tab(df, selected_df, reservas, capitao_row, capitao_nome, chosen_formation, super_sub_id, super_sub_pos_chosen, rodada_num, app_mode, active_token, api, scorer, mercado_data, partidas_data):
    # ATAQUE
    atacantes = selected_df[selected_df['Posicao'] == 'Atacante']
    if not atacantes.empty:
        st.html('<div class="sector-header">⚡ ATAQUE</div>')
        cols_ata = st.columns(len(atacantes))
        for idx, (_, p) in enumerate(atacantes.iterrows()):
            with cols_ata[idx]:
                render_player_card(p, is_captain=(p['Nome'] == capitao_nome))

    # MEIO-CAMPO
    meias = selected_df[selected_df['Posicao'] == 'Meia']
    if not meias.empty:
        st.html('<div class="sector-header">🎯 MEIO-CAMPO</div>')
        cols_mei = st.columns(len(meias))
        for idx, (_, p) in enumerate(meias.iterrows()):
            with cols_mei[idx]:
                render_player_card(p, is_captain=(p['Nome'] == capitao_nome))

    # DEFESA (Laterais & Zagueiros - Laterais nas pontas, Zagueiros no centro)
    defesa_raw = selected_df[selected_df['Posicao'].isin(['Lateral', 'Zagueiro'])]
    if not defesa_raw.empty:
        defesa = order_defensive_line(defesa_raw)
        st.html('<div class="sector-header">🛡️ LINHA DEFENSIVA</div>')
        cols_def = st.columns(len(defesa))
        for idx, (_, p) in enumerate(defesa.iterrows()):
            with cols_def[idx]:
                render_player_card(p, is_captain=(p['Nome'] == capitao_nome))

    # GOLEIRO & TÉCNICO
    gol_tec = selected_df[selected_df['Posicao'].isin(['Goleiro', 'Técnico'])]
    if not gol_tec.empty:
        st.html('<div class="sector-header">🧤 GOLEIRO & COMANDO TÉCNICO</div>')
        cols_base = st.columns([1, 1, 1, 1])
        goleiro_df = selected_df[selected_df['Posicao'] == 'Goleiro']
        tecnico_df = selected_df[selected_df['Posicao'] == 'Técnico']

        with cols_base[1]:
            if not goleiro_df.empty:
                render_player_card(goleiro_df.iloc[0], is_captain=(goleiro_df.iloc[0]['Nome'] == capitao_nome))
        with cols_base[2]:
            if not tecnico_df.empty:
                render_player_card(tecnico_df.iloc[0], is_captain=False)

    # BANCO DE RESERVAS EM CARDS
    if reservas:
        st.markdown("---")
        st.html('<div class="sector-header">🔄 BANCO DE RESERVAS (Troca Automática)</div>')

        res_cols = st.columns(len(reservas))
        for idx, (pos, r) in enumerate(reservas.items()):
            with res_cols[idx]:
                is_super = (pos == super_sub_pos_chosen)
                gain = r.get('Expected_Gain', 0) if hasattr(r, 'get') else 0
                render_player_card(r, is_super_sub=is_super, sub_gain=gain)

                # Seletor para troca manual de reserva desta posição com regras estritas
                starter_pos_players = selected_df[selected_df['Posicao'] == pos]
                if starter_pos_players.empty:
                    st.caption("Posição não usada nesta formação")
                    continue

                cheapest_price = round(float(starter_pos_players['Preco'].min()), 2)

                # Alerta caso o reserva atual viole a regra de preço após trocas de titulares
                curr_res_price = float(r.get('Preco', 0.0))
                if curr_res_price > cheapest_price:
                    st.error(f"⚠️ **Preço Excedido:** C$ {curr_res_price:.2f} > máx C$ {cheapest_price:.2f}")

                # Filtragem rigorosa oficial da Globo:
                # 1. Mesma posição
                # 2. Não pode estar entre os titulares
                # 3. Preço rigorosamente menor ou igual ao titular mais barato daquela posição
                # 4. Apenas atletas confirmados como Provável (Status_ID == 7)
                cond_pos = (df['Posicao'] == pos)
                cond_not_starter = (~df['ID'].isin(selected_df['ID'].tolist()))
                cond_price = (df['Preco'] <= cheapest_price)
                cond_status = (df['Status_ID'] == 7) if 'Status_ID' in df.columns else True

                available_bench_candidates = df[cond_pos & cond_not_starter & cond_price & cond_status].copy()

                if not available_bench_candidates.empty:
                    with st.popover(f"🔄 Trocar {pos[:3]}", use_container_width=True):
                        st.caption(f"Opções **Prováveis** para {pos} (máx. C$ {cheapest_price:.2f}):")
                        cand_list = available_bench_candidates.sort_values(by=['Upside', 'Media_Ajustada'], ascending=[False, False])
                        cand_labels = [f"{row['Nome']} ({row['Clube']} • C$ {row['Preco']:.2f} • xP {row['Media_Ajustada']:.2f} • 🟢 Provável)" for _, row in cand_list.iterrows()]
                        current_res_id = r.get('ID') if hasattr(r, 'get') else None
                        current_cand_idx = 0
                        for c_i, (_, c_row) in enumerate(cand_list.iterrows()):
                            if c_row['ID'] == current_res_id:
                                current_cand_idx = c_i
                                break
                        chosen_cand_label = st.selectbox(f"Selecione {pos}:", options=cand_labels, index=current_cand_idx, key=f"sel_bench_{pos}")
                        if st.button("Confirmar Reserva", key=f"btn_apply_bench_{pos}", use_container_width=True):
                            cand_selected_row = cand_list.iloc[cand_labels.index(chosen_cand_label)].copy()
                            if float(cand_selected_row['Preco']) > cheapest_price:
                                st.error(f"❌ **Regra Violada:** O atleta custa C$ {cand_selected_row['Preco']:.2f}, ultrapassando o limite de C$ {cheapest_price:.2f} (preço do titular mais barato de {pos}).")
                            elif cand_selected_row.get('Status_ID') and int(cand_selected_row.get('Status_ID')) != 7:
                                st.error("❌ **Status Inválido:** Apenas atletas 'Provável' são aceitos no banco de reservas.")
                            else:
                                worst_starter_xp = starter_pos_players['Media_Ajustada'].min() if not starter_pos_players.empty else 0.0
                                cand_selected_row['Worst_Starter_XP'] = worst_starter_xp
                                cand_selected_row['Expected_Gain'] = round(max(0.0, (cand_selected_row.get('Upside', cand_selected_row.get('Media_Ajustada', 0.0)) - worst_starter_xp) * 0.4), 2)
                                if "custom_reserves" not in st.session_state:
                                    st.session_state["custom_reserves"] = dict(reservas)
                                st.session_state["custom_reserves"][pos] = cand_selected_row
                                st.session_state["custom_mode_owner"] = app_mode
                                st.success(f"✅ {cand_selected_row['Nome']} definido como reserva de {pos}!")
                                st.rerun()

        super_r = reservas.get(super_sub_pos_chosen, list(reservas.values())[0])
        st.success(f"⭐ **Reserva de Luxo Ativo:** **{super_r['Nome']} ({super_r['Posicao']} - {super_r['Clube']})** | Teto: **{super_r.get('Upside', 0):.2f} pts**!")

        st.markdown("")
        tab_btn1, tab_btn2, tab_btn3 = st.columns(3)
        with tab_btn1:
            if st.button(f"💾 SALVAR NO APP (RODADA {rodada_num})", use_container_width=True, key="btn_save_tab_cards"):
                save_official_team(
                    rodada=rodada_num,
                    starters_df=selected_df,
                    captain_id=int(capitao_row['ID']),
                    reserves_dict=reservas,
                    super_sub_pos=super_sub_pos_chosen or "Atacante"
                )
                st.success(f"✅ Time da Rodada {rodada_num} salvo com sucesso!")
                st.rerun()
        with tab_btn2:
            if st.button("🚀 ESCALAR NO CARTOLA GLOBO", type="primary", use_container_width=True, key="btn_globo_autoscale_cards"):
                valid_lineup, val_errors = validate_lineup_rules(selected_df, reservas)
                if not valid_lineup:
                    for err in val_errors:
                        st.error(f"❌ {err}")
                else:
                    with st.spinner("Enviando escalação diretamente para a Globo..."):
                        token_to_use = active_token or (st.secrets.get("cartola_token", "") if hasattr(st, "secrets") else "")
                        success, resp_globo = api.save_time_to_globo(
                            token=token_to_use,
                            esquema_name=chosen_formation,
                            captain_id=int(capitao_row['ID']),
                            starters_ids=selected_df['ID'].tolist(),
                            reserves_dict=reservas,
                            super_sub_id=super_sub_id
                        )
                        handle_globo_escalacao_result(success, resp_globo, rodada_num, selected_df, capitao_row, reservas, super_sub_pos=super_sub_pos_chosen)
        with tab_btn3:
            if st.button("📥 PUXAR DA GLOBO", use_container_width=True, key="btn_sync_tab_cards", help="Sincroniza as alterações que você fez no app oficial do Cartola FC"):
                with st.spinner("📥 Sincronizando com a sua conta oficial do Cartola..."):
                    token_to_use = active_token or (st.secrets.get("cartola_token", "") if hasattr(st, "secrets") else "")
                    sync_ok, sync_msg = sync_team_from_globo(api, token_to_use, rodada_num, mercado_data, partidas_data, scorer)
                    if sync_ok:
                        st.success(f"✅ {sync_msg}")
                        time.sleep(1.2)
                        st.rerun()
                    else:
                        st.error(f"❌ {sync_msg}")


