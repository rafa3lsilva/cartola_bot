import pandas as pd
import streamlit as st

from ui.components import render_player_card


def render_comparison_tab(df, rodada_num, budget, max_per_club, chosen_formation, all_formations_summary, optimizer):
    st.subheader(f"📈 Comparativo de Esquemas Táticos • Rodada {rodada_num}")
    st.caption("O otimizador MILP calcula a melhor combinação matemática de atletas possível para cada uma das formações oficiais com base no seu patrimônio.")

    # Se não foi calculado previamente (ex: modo oficial ou formação fixa), calcula agora
    if all_formations_summary is None or len(all_formations_summary) <= 1:
        with st.spinner("Calculando a melhor escalação para todas as formações..."):
            _, _, _, all_formations_summary = optimizer.optimize_best_formation(
                df, budget=budget, max_players_per_club=max_per_club
            )

    if all_formations_summary:
        sorted_forms = sorted(all_formations_summary.items(), key=lambda x: x[1]['score'], reverse=True)
        best_overall_form = sorted_forms[0][0]
        best_overall_score = sorted_forms[0][1]['score']

        # 1. Cards Comparativos no Topo
        f_cols = st.columns(len(sorted_forms))
        for idx, (f_name, data) in enumerate(sorted_forms):
            with f_cols[idx]:
                is_best = (f_name == best_overall_form)
                is_active = (f_name == chosen_formation)
                bg_grad = "linear-gradient(135deg, #1e3a8a, #0f172a)" if is_best else "#1e293b"
                border_c = "#38bdf8" if is_best else ("#f59e0b" if is_active else "#334155")
                badge_label = "🏆 CAMPEÃ GLOBAL" if is_best else ("⭐ ATIVA" if is_active else f"{f_name}")

                st.html(f'''
                <div class="metric-card" style="background:{bg_grad}; border:2px solid {border_c}; padding:10px 6px;">
                    <div style="font-size:0.68rem; font-weight:800; color:{border_c}; margin-bottom:2px;">{badge_label}</div>
                    <div style="font-size:1.15rem; font-weight:900; color:#f8fafc;">{f_name}</div>
                    <div style="font-size:1.20rem; font-weight:900; color:#34d399; margin:4px 0;">{data['score']:.2f} <span style="font-size:0.75rem; color:#94a3b8;">xP</span></div>
                    <div style="font-size:0.70rem; color:#cbd5e1;">Custo: C$ {data['cost']:.2f}</div>
                </div>
                ''')

        st.markdown("")

        # 2. Tabela Comparativa Detalhada
        comp_data = []
        for f_name, data in sorted_forms:
            delta_pts = round(data['score'] - best_overall_score, 2)
            delta_str = "🏆 Melhor" if delta_pts == 0 else f"{delta_pts:.2f} pts"
            status_str = "🏆 Maior Pontuação" if f_name == best_overall_form else ("⭐ Sua Formação" if f_name == chosen_formation else "Opção")

            # Contagem de posições
            f_df = data['df']
            num_ata = len(f_df[f_df['Posicao'] == 'Atacante'])
            num_mei = len(f_df[f_df['Posicao'] == 'Meia'])
            num_zag = len(f_df[f_df['Posicao'] == 'Zagueiro'])
            num_lat = len(f_df[f_df['Posicao'] == 'Lateral'])

            comp_data.append({
                "Formação": f_name,
                "Pontos Esperados (xP)": f"{data['score']:.2f} pts",
                "Diferença p/ Líder": delta_str,
                "Custo Total": f"C$ {data['cost']:.2f}",
                "Estrutura Tática": f"{num_lat} LAT • {num_zag} ZAG • {num_mei} MEI • {num_ata} ATA",
                "Status": status_str
            })
        st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

        # 3. Expanders para Ver o Time Ideal de Cada Formação
        st.markdown("### 📋 Escalação Ideal por Formação")
        for f_name, data in sorted_forms:
            f_df = data['df']
            f_cap = f_df[f_df['Is_Capitao']].iloc[0]['Nome'] if 'Is_Capitao' in f_df.columns and f_df['Is_Capitao'].any() else f_df.iloc[0]['Nome']
            with st.expander(f"🔍 Ver time ideal na formação **{f_name}** ({data['score']:.2f} pts • C$ {data['cost']:.2f} • 👑 Capitão: {f_cap})"):
                cols_exp = st.columns(4)
                for ath_idx, (_, ath) in enumerate(f_df.iterrows()):
                    with cols_exp[ath_idx % 4]:
                        render_player_card(ath, is_captain=(ath['Nome'] == f_cap))

