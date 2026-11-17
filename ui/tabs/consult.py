import time

import pandas as pd
import streamlit as st

from cartola_bot.gsheets_manager import save_official_team
from cartola_bot.lineup_service import validate_lineup_rules
from ui.components import handle_globo_escalacao_result, render_consult_player_card
from ui.components import sync_team_from_globo_ui as sync_team_from_globo


def render_consult_tab(df, selected_df, reservas, capitao_row, chosen_formation, super_sub_id, super_sub_pos_chosen, rodada_num, budget, app_mode, active_token, api, scorer, optimizer, mercado_data, partidas_data):
    # 🔍 CONSULTOR TÁTICO & DIAGNÓSTICO ATLETA POR ATLETA
    st.subheader(f"🔍 Consultor Tático & Diagnóstico do Time (Rodada {rodada_num})")

    advisor_res = optimizer.analyze_user_lineup(
        df=df,
        selected_df=selected_df,
        captain_id=capitao_row['ID'],
        budget=budget
    )

    if advisor_res:
        # Banner de Veredito Geral
        st.html(f'''
        <div style="background:linear-gradient(135deg, #0f172a, #1e293b); border:2px solid {advisor_res['rating_color']}; border-radius:14px; padding:16px 20px; margin-bottom:20px;">
            <div style="font-size:1.35rem; font-weight:900; color:{advisor_res['rating_color']}; margin-bottom:4px;">
                {advisor_res['rating']}
            </div>
            <div style="font-size:0.90rem; color:#cbd5e1; margin-bottom:12px;">
                {advisor_res['rating_desc']}
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:10px;">
                <span class="consult-badge consult-badge-manter">✅ {advisor_res['manter_count']} Atletas Recomendados</span>
                <span class="consult-badge consult-badge-atencao">⚠️ {advisor_res['atencao_count']} Em Atenção / Aposta</span>
                <span class="consult-badge consult-badge-trocar">❌ {advisor_res['trocar_count']} Sugestões de Troca</span>
            </div>
        </div>
        ''')

        if advisor_res['trocar_count'] > 0 and advisor_res['total_gain_potential'] > 0:
            st.info(f"💡 **Potencial de Ganho:** Aplicando as substituições recomendadas pelo modelo abaixo, seu time pode ganhar aproximadamente **+{advisor_res['total_gain_potential']:.2f} pts** adicionais sem estourar o orçamento!")

        # Exibição Atleta por Atleta em 2 Colunas
        starters_list = advisor_res['starters']
        c_left, c_right = st.columns(2)
        for idx, s in enumerate(starters_list):
            target_col = c_left if idx % 2 == 0 else c_right
            with target_col:
                render_consult_player_card(s)
                sug = s.get('Sugestao_Troca')
                if sug:
                    if st.button(f"🔄 Aplicar Troca: Entra {sug['Nome']}", key=f"btn_apply_sug_{s['ID']}_{idx}", use_container_width=True):
                        target_out = s['Nome']
                        cand_row = df[df['ID'] == sug['ID']]
                        if not cand_row.empty:
                            new_row = cand_row.iloc[0].copy()
                            new_row['Is_Capitao'] = bool(s.get('Is_Capitao', False))
                            new_df = selected_df[selected_df['Nome'] != target_out].copy()
                            new_df = pd.concat([new_df, pd.DataFrame([new_row])], ignore_index=True)
                            st.session_state["custom_starters_df"] = new_df
                            st.session_state["custom_mode_owner"] = app_mode
                            st.success(f"✅ {target_out} substituído por {sug['Nome']}!")
                            st.rerun()

        # Ações Finais da Consultoria
        st.markdown("---")
        token_active = st.session_state.get("cartola_token", "")

        if token_active:
            btn_c1, btn_c2, btn_c3 = st.columns(3)
            with btn_c1:
                if st.button(f"💾 SALVAR NO APP (RODADA {rodada_num})", use_container_width=True, key="btn_save_advisor"):
                    best_res_pos_calc = None
                    max_up = -1.0
                    for pos, r in reservas.items():
                        up = r.get('Upside', r.get('Media_Ajustada', 0))
                        if up > max_up:
                            max_up = up
                            best_res_pos_calc = pos

                    save_official_team(
                        rodada=rodada_num,
                        starters_df=selected_df,
                        captain_id=int(capitao_row['ID']),
                        reserves_dict=reservas,
                        super_sub_pos=super_sub_pos_chosen or best_res_pos_calc or "Atacante"
                    )
                    st.success(f"✅ Time da Rodada {rodada_num} salvo com sucesso!")
                    st.rerun()
            with btn_c2:
                if st.button("🚀 ESCALAR NO CARTOLA GLOBO", type="primary", use_container_width=True, key="btn_globo_autoscale"):
                    valid_lineup, val_errors = validate_lineup_rules(selected_df, reservas)
                    if not valid_lineup:
                        for err in val_errors:
                            st.error(f"❌ {err}")
                    else:
                        with st.spinner("Enviando escalação diretamente para os servidores da Globo..."):
                            success, resp_globo = api.save_time_to_globo(
                                token=token_active,
                                esquema_name=chosen_formation,
                                captain_id=int(capitao_row['ID']),
                                starters_ids=selected_df['ID'].tolist(),
                                reserves_dict=reservas,
                                super_sub_id=super_sub_id
                            )
                            handle_globo_escalacao_result(success, resp_globo, rodada_num, selected_df, capitao_row, reservas, super_sub_pos=super_sub_pos_chosen)
            with btn_c3:
                if st.button("📥 PUXAR DA GLOBO", use_container_width=True, key="btn_sync_advisor", help="Importa alterações feitas no app oficial do Cartola"):
                    with st.spinner("📥 Sincronizando com a sua conta do Cartola FC..."):
                        sync_ok, sync_msg = sync_team_from_globo(api, token_active, rodada_num, mercado_data, partidas_data, scorer)
                        if sync_ok:
                            st.success(f"✅ {sync_msg}")
                            time.sleep(1.2)
                            st.rerun()
                        else:
                            st.error(f"❌ {sync_msg}")
        else:
            act_col1, act_col2 = st.columns([3, 2])
            with act_col1:
                st.write("🛡️ **Pronto para a rodada?** Salve este time para travar sua escalação oficial e acompanhar parciais ao vivo.")
            with act_col2:
                if st.button(f"💾 SALVAR COMO TIME OFICIAL (R{rodada_num})", type="primary", use_container_width=True, key="btn_save_advisor"):
                    save_official_team(
                        rodada=rodada_num,
                        starters_df=selected_df,
                        captain_id=int(capitao_row['ID']),
                        reserves_dict=reservas,
                        super_sub_pos=super_sub_pos_chosen or "Atacante"
                    )
                    st.success(f"✅ Time da Rodada {rodada_num} salvo como Oficial com sucesso!")
                    st.rerun()


