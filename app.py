import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

from cartola_bot.api import CartolaAPI
from cartola_bot.scoring import Scorer
from cartola_bot.solver import TeamOptimizer
from cartola_bot.exporter import Exporter
from cartola_bot.utils.config_loader import load_config

# Configuração da página para máxima responsividade
st.set_page_config(
    page_title="Cartola FC Optimizer Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="auto"
)

# Estilização CSS personalizada para visual de Cards e Campo Tático
st.html("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #38bdf8;
        text-align: center;
        margin-bottom: 2px;
        text-shadow: 0 2px 10px rgba(56, 189, 248, 0.2);
    }
    .sub-header {
        font-size: 0.95rem;
        color: #94a3b8;
        text-align: center;
        margin-bottom: 20px;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border-radius: 12px;
        padding: 14px;
        border: 1px solid #334155;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
        margin-bottom: 15px;
    }
    .metric-title {
        font-size: 0.80rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .sector-header {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-top: 15px;
        margin-bottom: 10px;
        border-left: 4px solid #38bdf8;
        padding-left: 10px;
    }
    /* Estilo do Card do Jogador com altura e alinhamento padronizados */
    .player-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 12px 8px;
        text-align: center;
        position: relative;
        transition: transform 0.2s, box-shadow 0.2s;
        margin-bottom: 12px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        height: 255px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        box-sizing: border-box;
    }
    .player-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 18px rgba(0,0,0,0.35);
        border-color: #475569;
    }
    .player-card-captain {
        background: linear-gradient(145deg, #2a2415, #1e1b10);
        border: 2px solid #f59e0b;
        box-shadow: 0 0 15px rgba(245, 158, 11, 0.25);
    }
    .player-card-super-sub {
        background: linear-gradient(145deg, #132e23, #0d1e17);
        border: 2px solid #10b981;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.25);
    }
    .badge-captain {
        position: absolute;
        top: 8px;
        left: 8px;
        background: #f59e0b;
        color: #000;
        font-size: 0.65rem;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 6px;
        text-transform: uppercase;
        z-index: 2;
    }
    .badge-pos {
        position: absolute;
        top: 8px;
        right: 8px;
        background: #334155;
        color: #94a3b8;
        font-size: 0.65rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 6px;
        z-index: 2;
    }
    .card-top {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .player-photo {
        width: 62px;
        height: 62px;
        border-radius: 50%;
        object-fit: cover;
        margin: 6px auto 6px auto;
        display: block;
        background: #0f172a;
        border: 2px solid #475569;
    }
    .club-crest {
        width: 18px;
        height: 18px;
        vertical-align: middle;
        margin-right: 4px;
    }
    .player-name {
        font-size: 0.90rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 95%;
        height: 20px;
        line-height: 20px;
    }
    .player-club {
        font-size: 0.75rem;
        color: #94a3b8;
        height: 20px;
        line-height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .card-bottom {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-end;
        min-height: 52px;
    }
    .stat-badge {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
        margin: 1px;
    }
    .badge-price {
        background: #0f172a;
        color: #fbbf24;
        border: 1px solid #334155;
    }
    .badge-xp {
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }
    .badge-sg {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    .swap-gain-box {
        font-size: 0.70rem;
        color: #4ade80;
        font-weight: 700;
        height: 16px;
        line-height: 16px;
        margin-top: 2px;
    }
    /* Estilo do Card do Perfil do Time na Sidebar */
    .team-profile-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #172554 100%);
        border: 1px solid #3b82f6;
        border-radius: 16px;
        padding: 16px 12px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 8px 20px rgba(59, 130, 246, 0.15);
    }
    .team-shield {
        font-size: 2.2rem;
        margin-bottom: 4px;
        filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.5));
    }
    .team-title {
        font-size: 1.35rem;
        font-weight: 900;
        color: #f8fafc;
        letter-spacing: 1px;
        margin-bottom: 2px;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
    }
    .team-subtitle {
        font-size: 0.75rem;
        font-weight: 600;
        color: #38bdf8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .market-status-pill {
        display: inline-flex;
        align-items: center;
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.70rem;
        font-weight: 700;
    }
    .sidebar-section {
        font-size: 0.80rem;
        font-weight: 800;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 15px;
        margin-bottom: 6px;
        border-bottom: 1px solid #334155;
        padding-bottom: 4px;
    }
    .sidebar-footer {
        text-align: center;
        color: #64748b;
        font-size: 0.70rem;
        margin-top: 25px;
        padding-top: 10px;
        border-top: 1px solid #1e293b;
    }
    /* Estilos dos Cards de Parciais Ao Vivo */
    .live-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 12px 8px;
        text-align: center;
        position: relative;
        height: 275px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        box-sizing: border-box;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    .live-card-playing {
        border-color: #38bdf8;
        box-shadow: 0 0 14px rgba(56, 189, 248, 0.25);
    }
    .live-card-captain {
        background: linear-gradient(145deg, #2a2415, #1e1b10);
        border: 2px solid #f59e0b;
        box-shadow: 0 0 15px rgba(245, 158, 11, 0.3);
    }
    .live-card-super-sub {
        background: linear-gradient(145deg, #132e23, #0d1e17);
        border: 2px solid #10b981;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
    }
    .live-score-box {
        background: rgba(15, 23, 42, 0.95);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 6px 10px;
        margin: 4px 0;
        width: 90%;
    }
    .live-score-val {
        font-size: 1.35rem;
        font-weight: 900;
        color: #34d399;
    }
    .live-score-waiting {
        font-size: 0.85rem;
        font-weight: 700;
        color: #94a3b8;
    }
    .live-scouts-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 3px;
        min-height: 24px;
    }
    .scout-chip {
        font-size: 0.65rem;
        font-weight: 800;
        padding: 2px 5px;
        border-radius: 4px;
        background: #334155;
        color: #f1f5f9;
    }
    .scout-chip-g { background: #059669; color: #fff; }
    .scout-chip-a { background: #0284c7; color: #fff; }
    .scout-chip-ds { background: #4f46e5; color: #fff; }
    .scout-chip-de { background: #d97706; color: #fff; }
    .scout-chip-sg { background: #16a34a; color: #fff; }
    .scout-chip-ca { background: #eab308; color: #000; }
    .scout-chip-cv { background: #dc2626; color: #fff; }
    @media (max-width: 768px) {
        .main-header { font-size: 1.6rem; }
        .metric-value { font-size: 1.25rem; }
        .player-card, .live-card { height: 250px; padding: 8px 4px; }
        .player-photo { width: 48px; height: 48px; }
        .player-name { font-size: 0.80rem; }
        .live-score-val { font-size: 1.15rem; }
    }
</style>
""")

@st.cache_data(ttl=600)
def load_app_data(use_cache=True):
    """Carrega dados da API e inicializa os módulos."""
    config = load_config()
    api = CartolaAPI(config)
    mercado_data = api.get_mercado(use_cache=use_cache)
    partidas_data = api.get_partidas(use_cache=use_cache)
    return config, mercado_data, partidas_data

def render_player_card(p, is_captain=False, is_super_sub=False, sub_gain=None):
    """Renderiza um card visual elegante para um jogador."""
    nome = p.get('Nome', 'Sem Nome')
    pos = p.get('Posicao', '')
    clube = p.get('Clube', '')
    preco = p.get('Preco', 0.0)
    media = p.get('Media', 0.0)
    xp_val = p.get('Media_Ajustada', 0.0) * (1.5 if is_captain else 1.0)
    sg_prob = p.get('SG_Prob', None)
    foto = p.get('Foto', '') or "https://s3.glbimg.com/v1/AUTH_58d78b787ec34892b5aaa0c7a146155f/clubes_2026/silhuetas/generica.png"
    escudo = p.get('Escudo', '')

    card_class = "player-card"
    if is_captain:
        card_class += " player-card-captain"
    elif is_super_sub:
        card_class += " player-card-super-sub"

    captain_html = '<div class="badge-captain">👑 CAPITÃO</div>' if is_captain else ''
    super_sub_html = '<div class="badge-captain" style="background:#10b981;color:#fff;">⭐ RESERVA LUXO</div>' if is_super_sub else ''
    badge_html = super_sub_html if is_super_sub else captain_html

    escudo_html = f'<img src="{escudo}" class="club-crest"/>' if escudo else ''
    sg_html = f'<span class="stat-badge badge-sg">🛡️ {sg_prob:.0f}%</span>' if (sg_prob is not None and pos in ['Goleiro', 'Lateral', 'Zagueiro']) else ''
    gain_html = f'<div class="swap-gain-box">Troca: +{sub_gain:.2f} pts</div>' if (sub_gain and sub_gain > 0) else '<div class="swap-gain-box"></div>'

    html = (
        f'<div class="{card_class}">'
        f'{badge_html}'
        f'<div class="badge-pos">{pos[:3].upper()}</div>'
        f'<div class="card-top">'
        f'<img src="{foto}" class="player-photo" onerror="this.src=\'https://s3.glbimg.com/v1/AUTH_58d78b787ec34892b5aaa0c7a146155f/clubes_2026/silhuetas/generica.png\';"/>'
        f'<div class="player-name" title="{nome}">{nome}</div>'
        f'<div class="player-club">{escudo_html}<span>{clube} • Méd {media:.1f}</span></div>'
        f'</div>'
        f'<div class="card-bottom">'
        f'<div>'
        f'<span class="stat-badge badge-price">C$ {preco:.2f}</span>'
        f'<span class="stat-badge badge-xp">⚡ {xp_val:.2f}</span>'
        f'{sg_html}'
        f'</div>'
        f'{gain_html}'
        f'</div>'
        f'</div>'
    )
    st.html(html)

def render_live_player_card(p, pinfo=None, is_captain=False, is_super_sub=False):
    """Renderiza um card visual de acompanhamento ao vivo."""
    nome = p.get('Nome', 'Sem Nome')
    pos = p.get('Posicao', '')
    clube = p.get('Clube', '')
    foto = p.get('Foto', '') or "https://s3.glbimg.com/v1/AUTH_58d78b787ec34892b5aaa0c7a146155f/clubes_2026/silhuetas/generica.png"
    escudo = p.get('Escudo', '')

    has_played = (pinfo is not None)
    card_class = "live-card"
    if has_played:
        card_class += " live-card-playing"
    if is_captain:
        card_class += " live-card-captain"
    elif is_super_sub:
        card_class += " live-card-super-sub"

    captain_html = '<div class="badge-captain">👑 CAPITÃO (1.5x)</div>' if is_captain else ''
    super_sub_html = '<div class="badge-captain" style="background:#10b981;color:#fff;">⭐ RESERVA LUXO</div>' if is_super_sub else ''
    badge_html = super_sub_html if is_super_sub else captain_html
    escudo_html = f'<img src="{escudo}" class="club-crest"/>' if escudo else ''

    if has_played:
        pts_bruto = float(pinfo.get('pontuacao', 0.0))
        pts_calc = pts_bruto * 1.5 if is_captain else pts_bruto
        pts_color = "#34d399" if pts_calc >= 0 else "#f87171"
        sub_txt = f'<div style="font-size:0.65rem;color:#f59e0b;">(Base: {pts_bruto:.2f} pts)</div>' if is_captain else ''
        
        score_box_html = (
            f'<div class="live-score-box">'
            f'<div class="live-score-val" style="color:{pts_color};">{pts_calc:+.2f} <span style="font-size:0.8rem;">pts</span></div>'
            f'{sub_txt}'
            f'</div>'
        )
        
        # Scouts Chips (Garante dicionário mesmo se a API retornar None)
        scouts_raw = pinfo.get('scout') or {}
        scout_chips = []
        if isinstance(scouts_raw, dict):
            if scouts_raw.get('G'): scout_chips.append(f'<span class="scout-chip scout-chip-g">⚽ {scouts_raw["G"]}G</span>')
            if scouts_raw.get('A'): scout_chips.append(f'<span class="scout-chip scout-chip-a">🎯 {scouts_raw["A"]}A</span>')
            if scouts_raw.get('DS'): scout_chips.append(f'<span class="scout-chip scout-chip-ds">🛡️ {scouts_raw["DS"]}DS</span>')
            if scouts_raw.get('DE'): scout_chips.append(f'<span class="scout-chip scout-chip-de">🧤 {scouts_raw["DE"]}DE</span>')
            if scouts_raw.get('SG'): scout_chips.append(f'<span class="scout-chip scout-chip-sg">🛡️ SG</span>')
            if scouts_raw.get('CA'): scout_chips.append(f'<span class="scout-chip scout-chip-ca">🟨 {scouts_raw["CA"]}CA</span>')
            if scouts_raw.get('CV'): scout_chips.append(f'<span class="scout-chip scout-chip-cv">🟥 {scouts_raw["CV"]}CV</span>')
        
        chips_html = "".join(scout_chips) if scout_chips else '<span style="font-size:0.70rem;color:#94a3b8;">Em campo</span>'
    else:
        score_box_html = (
            f'<div class="live-score-box">'
            f'<div class="live-score-waiting">⏳ AGUARDANDO</div>'
            f'<div style="font-size:0.65rem;color:#64748b;">Ainda não jogou</div>'
            f'</div>'
        )
        chips_html = '<span style="font-size:0.70rem;color:#64748b;">Jogo a iniciar</span>'

    html = (
        f'<div class="{card_class}">'
        f'{badge_html}'
        f'<div class="badge-pos">{pos[:3].upper()}</div>'
        f'<div class="card-top">'
        f'<img src="{foto}" class="player-photo" onerror="this.src=\'https://s3.glbimg.com/v1/AUTH_58d78b787ec34892b5aaa0c7a146155f/clubes_2026/silhuetas/generica.png\';"/>'
        f'<div class="player-name" title="{nome}">{nome}</div>'
        f'<div class="player-club">{escudo_html}<span>{clube}</span></div>'
        f'</div>'
        f'{score_box_html}'
        f'<div class="live-scouts-container">{chips_html}</div>'
        f'</div>'
    )
    st.html(html)

def main():
    st.html('<div class="main-header">🛡️ M1TOS EC • Cartola Pro</div><div class="sub-header">Otimizador Tático Inteligente com Pontuação Esperada (xP) & Reserva de Luxo</div>')

    with st.sidebar:
        # Card do Perfil do Time M1TOS EC
        st.html('''
        <div class="team-profile-card">
            <div class="team-shield">🏆</div>
            <div class="team-title">M1TOS EC</div>
            <div class="team-subtitle">Cartola FC • Temporada 2026</div>
            <div class="market-status-pill">🟢 DADOS OFICIAIS ATIVOS</div>
        </div>
        ''')
        
        config_preview = load_config()
        default_budget = float(config_preview.get('defaults', {}).get('budget', 146.07))
        
        # Seção 1: Cofre
        st.html('<div class="sidebar-section">💰 PATRIMÔNIO DISPONÍVEL</div>')
        budget = st.number_input(
            "Saldo em Cartoletas (C$):",
            min_value=50.0,
            max_value=400.0,
            value=default_budget,
            step=1.0,
            format="%.2f",
            help="Total de cartoletas disponíveis para escalar o time titular do M1TOS EC."
        )
        
        # Seção 2: Estratégia Tática
        st.html('<div class="sidebar-section">📋 ESTRATÉGIA TÁTICA</div>')
        available_formations = ["auto"] + list(config_preview.get('formations', {}).keys())
        formation_option = st.selectbox(
            "Esquema Tático:",
            options=available_formations,
            format_func=lambda x: "⭐ Automática (Melhor Formação)" if x == "auto" else f"Formação {x}",
            index=0,
            help="A opção Automática testa todas as 5 formações e escolhe a que projeta a maior pontuação global."
        )
        
        max_per_club = st.slider(
            "Máx. Jogadores por Clube:",
            min_value=2,
            max_value=7,
            value=5,
            help="Limite de segurança para evitar dependência excessiva de uma única equipe."
        )
        
        # Seção 3: Conexão com a API
        st.html('<div class="sidebar-section">🔄 ATUALIZAÇÃO DA API</div>')
        force_refresh = st.checkbox("Forçar atualização ao vivo da Globo", value=False)
        
        st.markdown("")
        run_button = st.button("🚀 ESCALAR M1TOS EC", type="primary", use_container_width=True)
        
        # Rodapé da Sidebar
        st.html('''
        <div class="sidebar-footer">
            M1TOS EC • Powered by MILP Optimization<br>
            © 2026 Cartola Bot Pro
        </div>
        ''')

    try:
        config, mercado_data, partidas_data = load_app_data(use_cache=not force_refresh)
        api = CartolaAPI(config)
        scorer = Scorer(config)
        optimizer = TeamOptimizer(config)
        exporter = Exporter()
        
        rodada_num = partidas_data.get('rodada', '?')
        st.info(f"🏆 **Rodada {rodada_num} do Brasileirão** analisada com sucesso!")
        
        with st.spinner("Calculando a melhor combinação matemática..."):
            df = scorer.process_data(mercado_data, partidas_data)
            
            if df.empty:
                st.error("Nenhum atleta provável disponível para otimização.")
                return
                
            all_formations_summary = None
            if formation_option == "auto":
                chosen_formation, selected_df, best_score, all_formations_summary = optimizer.optimize_best_formation(
                    df, budget=budget, max_players_per_club=max_per_club
                )
            else:
                chosen_formation = formation_option
                selected_df = optimizer.optimize(
                    df, budget=budget, formation_name=chosen_formation, max_players_per_club=max_per_club
                )

        if selected_df is None or selected_df.empty:
            st.error("Não foi possível montar um time completo com esse orçamento. Tente aumentar o valor em cartoletas.")
            return

        reservas = optimizer.get_reservas(df, selected_df)
        
        capitao_row = selected_df[selected_df['Is_Capitao']].iloc[0] if 'Is_Capitao' in selected_df.columns and selected_df['Is_Capitao'].any() else selected_df.iloc[0]
        capitao_nome = capitao_row['Nome']
        capitao_extra = capitao_row['Media_Ajustada'] * 0.5
        total_xp = selected_df['Media_Ajustada'].sum() + capitao_extra
        total_cost = selected_df['Preco'].sum()
        budget_left = budget - total_cost

        # 1. Cards de Resumo no Topo
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.html(f'<div class="metric-card"><div class="metric-title">🚀 Pontuação Esperada</div><div class="metric-value">{total_xp:.2f} pts</div></div>')
        with c2:
            st.html(f'<div class="metric-card"><div class="metric-title">💎 Custo dos Titulares</div><div class="metric-value">C$ {total_cost:.2f}</div></div>')
        with c3:
            st.html(f'<div class="metric-card"><div class="metric-title">🏦 Sobra no Caixa</div><div class="metric-value">C$ {budget_left:.2f}</div></div>')
        with c4:
            st.html(f'<div class="metric-card"><div class="metric-title">📋 Formação Tática</div><div class="metric-value">{chosen_formation}</div></div>')

        # 2. Alternador de Visualização (Cards vs Parciais vs Tabela)
        tab_cards, tab_live, tab_table, tab_comp = st.tabs([
            "🏟️ Escalação Tática (Cards)", 
            "🔴 Parciais Ao Vivo", 
            "📊 Tabela Detalhada", 
            "📈 Comparativo de Formações"
        ])

        with tab_cards:
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

            # DEFESA (Laterais & Zagueiros)
            defesa = selected_df[selected_df['Posicao'].isin(['Lateral', 'Zagueiro'])]
            if not defesa.empty:
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
                
                best_res_pos = None
                max_upside = -1.0
                for pos, r in reservas.items():
                    up = r.get('Upside', r.get('Media_Ajustada', 0))
                    if up > max_upside:
                        max_upside = up
                        best_res_pos = pos
                        
                res_cols = st.columns(len(reservas))
                for idx, (pos, r) in enumerate(reservas.items()):
                    with res_cols[idx]:
                        is_super = (pos == best_res_pos)
                        gain = r.get('Expected_Gain', 0)
                        render_player_card(r, is_super_sub=is_super, sub_gain=gain)

                super_r = reservas[best_res_pos]
                st.success(f"🌟 **Marque a estrelinha de Reserva de Luxo no Cartola em:** **{super_r['Nome']} ({super_r['Posicao']} - {super_r['Clube']})** | Teto: **{super_r.get('Upside', 0):.2f} pts**!")

        with tab_live:
            # 🔴 PARCIAIS AO VIVO
            col_l1, col_l2 = st.columns([3, 1])
            with col_l1:
                st.subheader(f"🔴 Parciais em Tempo Real • M1TOS EC (Rodada {rodada_num})")
            with col_l2:
                refresh_live = st.button("🔄 Atualizar Parciais", use_container_width=True)

            pontuados_data = api.get_pontuados()
            pontuados = pontuados_data.get('atletas', {})
            total_pontuados_count = len(pontuados)

            if total_pontuados_count == 0:
                st.info("ℹ️ Os jogos da rodada ainda não começaram ou os scouts ao vivo ainda não foram abertos pela Globo. Assim que os jogos começarem, as parciais aparecerão aqui automaticamente!")
            else:
                st.caption(f"📡 Dados ao vivo sincronizados com a Globo • {total_pontuados_count} atletas já pontuaram na rodada.")

            # Calcular parciais do time
            live_rows = []
            total_live_pts = 0.0
            jogadores_jogando = 0
            
            # Mapear pontuações por posição para checagem do reserva de luxo
            pos_starter_scores = {'Goleiro': [], 'Lateral': [], 'Zagueiro': [], 'Meia': [], 'Atacante': []}

            for _, p in selected_df.iterrows():
                atleta_id_str = str(p.get('ID'))
                is_cap = (p['Nome'] == capitao_nome)
                
                if atleta_id_str in pontuados:
                    pinfo = pontuados[atleta_id_str]
                    pts_bruto = float(pinfo.get('pontuacao', 0.0))
                    pts_calc = pts_bruto * 1.5 if is_cap else pts_bruto
                    total_live_pts += pts_calc
                    jogadores_jogando += 1
                    status_live = f"🟢 {pts_bruto:.2f} pts"
                    
                    scouts_raw = pinfo.get('scout', {})
                    scouts_str = ", ".join([f"{k}:{v}" for k, v in scouts_raw.items()]) if scouts_raw else "Em campo"
                else:
                    pts_bruto = None
                    pts_calc = 0.0
                    status_live = "⏳ Aguardando jogo"
                    scouts_str = "-"

                if p['Posicao'] in pos_starter_scores and pts_bruto is not None:
                    pos_starter_scores[p['Posicao']].append({'Nome': p['Nome'], 'pts': pts_bruto})

                nome_disp = f"👑 {p['Nome']} [C]" if is_cap else p['Nome']
                live_rows.append({
                    "Posição": p['Posicao'],
                    "Jogador": nome_disp,
                    "Clube": p['Clube'],
                    "Status / Pontos": status_live,
                    "Pontos c/ Capitão": f"{pts_calc:.2f} pts" if pts_bruto is not None else "-",
                    "Scouts na Partida": scouts_str
                })

            # Card de Pontuação Parcial Total
            st.html(f'''
            <div class="metric-card" style="background:linear-gradient(135deg, #1e3a8a, #0f172a); border:2px solid #38bdf8;">
                <div class="metric-title" style="color:#38bdf8;">⚡ PONTUAÇÃO PARCIAL TOTAL DO M1TOS EC</div>
                <div class="metric-value" style="font-size:2.2rem; color:#f8fafc;">{total_live_pts:.2f} <span style="font-size:1.1rem; color:#38bdf8;">pts</span></div>
                <div style="font-size:0.80rem; color:#94a3b8; margin-top:4px;">{jogadores_jogando} de 12 atletas já entraram em campo</div>
            </div>
            ''')

            # Checagem ao vivo do Reserva de Luxo
            best_res_pos = None
            max_upside = -1.0
            for pos, r in reservas.items():
                up = r.get('Upside', r.get('Media_Ajustada', 0))
                if up > max_upside:
                    max_upside = up
                    best_res_pos = pos

            if best_res_pos and best_res_pos in reservas:
                super_res = reservas[best_res_pos]
                res_id_str = str(super_res.get('ID'))
                
                if res_id_str in pontuados:
                    pts_res = float(pontuados[res_id_str].get('pontuacao', 0.0))
                    titulares_pos = pos_starter_scores.get(best_res_pos, [])
                    
                    if titulares_pos:
                        min_tit = min(titulares_pos, key=lambda x: x['pts'])
                        if pts_res > min_tit['pts']:
                            diff = pts_res - min_tit['pts']
                            st.success(f"🎉 **TROCA AUTOMÁTICA ATIVA AO VIVO!** O Reserva de Luxo **{super_res['Nome']} ({pts_res:.2f} pts)** superou **{min_tit['Nome']} ({min_tit['pts']:.2f} pts)**! Ganho real: **+{diff:.2f} pts** no M1TOS EC!")
                        else:
                            st.info(f"🔄 **Reserva de Luxo:** {super_res['Nome']} fez {pts_res:.2f} pts. Para entrar, precisa superar {min_tit['Nome']} ({min_tit['pts']:.2f} pts).")
                    else:
                        st.info(f"🔄 **Reserva de Luxo:** {super_res['Nome']} já jogou e fez **{pts_res:.2f} pts**! Aguardando os titulares da posição jogarem.")
                else:
                    st.info(f"⭐ **Reserva de Luxo Oficial:** {super_res['Nome']} ({super_res['Posicao']} - {super_res['Clube']}) ainda não jogou.")

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

            # DEFESA AO VIVO
            defesa = selected_df[selected_df['Posicao'].isin(['Lateral', 'Zagueiro'])]
            if not defesa.empty:
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

        with tab_table:
            # Tabela Tradicional para quem quiser consultar números
            pos_order = ['Goleiro', 'Lateral', 'Zagueiro', 'Meia', 'Atacante', 'Técnico']
            table_rows = []
            for pos in pos_order:
                players = selected_df[selected_df['Posicao'] == pos]
                for _, p in players.iterrows():
                    is_cap = p['Nome'] == capitao_nome
                    nome_display = f"👑 {p['Nome']} [CAPITÃO]" if is_cap else p['Nome']
                    xp_val = p['Media_Ajustada'] * 1.5 if is_cap else p['Media_Ajustada']
                    sg_val = f"{p['SG_Prob']:.0f}%" if ('SG_Prob' in p and p['Posicao'] in ['Goleiro', 'Lateral', 'Zagueiro']) else "-"
                    table_rows.append({
                        "Posição": p['Posicao'],
                        "Jogador": nome_display,
                        "Clube": p['Clube'],
                        "Preço (C$)": f"C$ {p['Preco']:.2f}",
                        "Média Hist.": f"{p['Media']:.2f}",
                        "Chance SG": sg_val,
                        "Mín. Val.": f"C$ {p['Min_Val']:.2f}",
                        "xP Esperado": f"{xp_val:.2f} pts"
                    })
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        with tab_comp:
            if all_formations_summary and len(all_formations_summary) > 1:
                comp_data = []
                for f_name, data in sorted(all_formations_summary.items(), key=lambda x: x[1]['score'], reverse=True):
                    comp_data.append({
                        "Formação": f_name,
                        "Pontos Esperados (xP)": f"{data['score']:.2f} pts",
                        "Custo (C$)": f"C$ {data['cost']:.2f}",
                        "Status": "⭐ ESCOLHIDA" if f_name == chosen_formation else ""
                    })
                st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

        # Botões de Download
        st.markdown("---")
        col_exp1, col_exp2 = st.columns(2)
        csv_path, img_path = exporter.export_files(selected_df, reservas, budget, formation=chosen_formation)
        
        with col_exp1:
            with open(csv_path, "rb") as f:
                st.download_button("📄 Baixar Escalação em CSV", data=f, file_name=os.path.basename(csv_path), mime="text/csv", use_container_width=True)
        with col_exp2:
            with open(img_path, "rb") as f:
                st.download_button("🖼️ Baixar Imagem da Escalação (PNG)", data=f, file_name=os.path.basename(img_path), mime="image/png", use_container_width=True)

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os dados: {e}")
        import traceback
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()

