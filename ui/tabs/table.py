import pandas as pd
import streamlit as st


def render_table_tab(selected_df, capitao_nome):
    # Tabela Tradicional para quem quiser consultar números
    pos_order = ['Goleiro', 'Lateral', 'Zagueiro', 'Meia', 'Atacante', 'Técnico']
    table_rows = []
    for pos in pos_order:
        players = selected_df[selected_df['Posicao'] == pos]
        for _, p in players.iterrows():
            is_cap = p['Nome'] == capitao_nome
            nome_display = f"👑 {p['Nome']} [CAPITÃO]" if is_cap else p['Nome']
            xp_val = p['Media_Ajustada'] * 1.5 if is_cap else p['Media_Ajustada']
            media_val = f"{p['Media']:.2f}" if ('Media' in p and pd.notna(p['Media'])) else f"{p.get('Media_Ajustada', 0.0):.2f}"
            min_val = f"C$ {p['Min_Val']:.2f}" if ('Min_Val' in p and pd.notna(p['Min_Val'])) else f"C$ {(p.get('Preco', 0.0) * 0.37):.2f}"
            sg_val = f"{p['SG_Prob']:.0f}%" if ('SG_Prob' in p and pd.notna(p['SG_Prob']) and p['Posicao'] in ['Goleiro', 'Lateral', 'Zagueiro']) else "-"
            table_rows.append({
                "Posição": p['Posicao'],
                "Jogador": nome_display,
                "Clube": p['Clube'],
                "Preço (C$)": f"C$ {p['Preco']:.2f}",
                "Média Hist.": media_val,
                "Chance SG": sg_val,
                "Mín. Val.": min_val,
                "xP Esperado": f"{xp_val:.2f} pts"
            })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

