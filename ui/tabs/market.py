import pandas as pd
import streamlit as st

from ui.components import render_market_player_card


def render_market_tab(df, selected_df, rodada_num, app_mode):
    # 🛒 MERCADO DE ATLETAS COM TAGS INTELIGENTES
    st.subheader(f"🛒 Mercado Oficial de Atletas • Rodada {rodada_num}")
    st.caption("Explore os atletas com tags de recomendação geradas pelo modelo matemático. Use a busca e filtros para montar ou ajustar sua equipe.")

    # Filtros do Mercado
    f_col1, f_col2, f_col3, f_col4 = st.columns([1.5, 1.5, 1.5, 2.5])
    with f_col1:
        pos_filter = st.selectbox("Posição:", ["Todas", "Goleiro", "Lateral", "Zagueiro", "Meia", "Atacante", "Técnico"], index=0)
    with f_col2:
        club_list = ["Todos"] + sorted(list(df['Clube'].unique()))
        club_filter = st.selectbox("Clube:", club_list, index=0)
    with f_col3:
        tag_filter = st.selectbox("Tag do Modelo:", ["Todas", "Excelente", "Boa Opção", "Aposta", "Evitar"], index=0)
    with f_col4:
        search_query = st.text_input("🔍 Buscar Atleta:", placeholder="Digite o nome do jogador...")

    # Ordenação
    ord_col1, ord_col2 = st.columns([2, 2])
    with ord_col1:
        sort_by = st.selectbox("Ordenar por:", [
            "Maior xP (Projetado)", "Menor Preço", "Maior Preço", "Maior Média Histórica", "Maior Teto (Upside)"
        ], index=0)

    # Filtrar DataFrame do Mercado
    m_df = df.copy()
    if pos_filter != "Todas":
        m_df = m_df[m_df['Posicao'] == pos_filter]
    if club_filter != "Todos":
        m_df = m_df[m_df['Clube'] == club_filter]
    if tag_filter != "Todas":
        m_df = m_df[m_df['Tag'] == tag_filter]
    if search_query:
        m_df = m_df[m_df['Nome'].str.contains(search_query, case=False, na=False)]

    # Aplicar Ordenação
    if sort_by == "Maior xP (Projetado)":
        m_df = m_df.sort_values(by="Media_Ajustada", ascending=False)
    elif sort_by == "Menor Preço":
        m_df = m_df.sort_values(by="Preco", ascending=True)
    elif sort_by == "Maior Preço":
        m_df = m_df.sort_values(by="Preco", ascending=False)
    elif sort_by == "Maior Média Histórica":
        m_df = m_df.sort_values(by="Media", ascending=False)
    elif sort_by == "Maior Teto (Upside)":
        m_df = m_df.sort_values(by="Upside", ascending=False)

    st.write(f"Exibindo **{len(m_df)}** atletas encontrados:")

    # Renderizar Grid do Mercado (4 por linha) com Ações Diretas
    grid_cols_num = 4
    selected_ids_set = set(selected_df['ID'].tolist())
    m_list = m_df.to_dict('records')
    for i in range(0, len(m_list), grid_cols_num):
        row_athletes = m_list[i:i+grid_cols_num]
        cols = st.columns(len(row_athletes))
        for idx, ath in enumerate(row_athletes):
            with cols[idx]:
                render_market_player_card(ath)
                ath_id = ath.get('ID')
                ath_pos = ath.get('Posicao')
                ath_name = ath.get('Nome')

                if ath_id in selected_ids_set:
                    st.html('<div style="text-align:center; padding:4px 0; font-size:0.80rem; font-weight:700; color:#10b981;">✅ Já Escalado</div>')
                else:
                    # Titulares na mesma posição disponíveis para serem substituídos
                    pos_starters = selected_df[selected_df['Posicao'] == ath_pos]
                    if not pos_starters.empty:
                        starter_names = pos_starters['Nome'].tolist()
                        with st.popover(f"➕ Escalar ({ath_pos[:3].upper()})", use_container_width=True):
                            st.write(f"**Escalar {ath_name}** no lugar de:")
                            target_starter = st.selectbox(
                                "Substituir quem?",
                                options=starter_names,
                                key=f"market_sub_target_{ath_id}_{i}"
                            )
                            if st.button("Confirmar Substituição", key=f"btn_confirm_market_sub_{ath_id}_{i}", type="primary", use_container_width=True):
                                out_p = selected_df[selected_df['Nome'] == target_starter].iloc[0]
                                new_row = pd.Series(ath).copy()
                                new_row['Is_Capitao'] = bool(out_p.get('Is_Capitao', False))
                                new_df = selected_df[selected_df['Nome'] != target_starter].copy()
                                new_df = pd.concat([new_df, pd.DataFrame([new_row])], ignore_index=True)
                                st.session_state["custom_starters_df"] = new_df
                                st.session_state["custom_mode_owner"] = app_mode
                                st.success(f"✅ {target_starter} substituído por {ath_name}!")
                                st.rerun()
                    else:
                        st.caption("Posição não usada nesta formação")

