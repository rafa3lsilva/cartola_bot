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

# Arquivo de persistência da escalação oficial
OFFICIAL_FILE = "time_oficial_ativo.json"

def load_official_team():
    """Carrega os dados do time oficial escalado a partir do arquivo JSON."""
    if os.path.exists(OFFICIAL_FILE):
        try:
            with open(OFFICIAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "rodada": 25,
        "starters_ids": [91101, 107093, 105531, 91772, 123445, 117632, 87747, 104783, 143193, 118844, 113103, 97341],
        "captain_id": 143193,
        "reserves_ids": {'Goleiro': 71631, 'Lateral': 91706, 'Zagueiro': 130307, 'Meia': 84626, 'Atacante': 114208},
        "super_sub_pos": "Atacante"
    }

def save_official_team(rodada, starters_ids, captain_id, reserves_ids, super_sub_pos="Atacante"):
    """Salva a escalação oficial como time ativo no arquivo JSON."""
    data = {
        "rodada": int(rodada),
        "updated_at": datetime.now().isoformat(),
        "starters_ids": [int(i) for i in starters_ids],
        "captain_id": int(captain_id),
        "reserves_ids": {pos: int(r_id) for pos, r_id in reserves_ids.items()},
        "super_sub_pos": super_sub_pos
    }
    with open(OFFICIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data

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
    
    /* Estilos do Mercado de Atletas e Consultor Tático */
    .market-player-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 10px 8px;
        text-align: center;
        position: relative;
        height: 285px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        box-sizing: border-box;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        margin-bottom: 10px;
    }
    .market-tag {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.68rem;
        font-weight: 800;
        text-transform: uppercase;
        margin-top: 2px;
    }
    .market-rationale {
        font-size: 0.70rem;
        color: #94a3b8;
        background: rgba(15, 23, 42, 0.7);
        border-radius: 6px;
        padding: 4px 6px;
        line-height: 1.25;
        width: 92%;
        min-height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    .consult-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 12px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .consult-badge {
        font-size: 0.70rem;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .consult-badge-manter {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .consult-badge-atencao {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .consult-badge-trocar {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .consult-rationale {
        font-size: 0.80rem;
        color: #e2e8f0;
        background: rgba(15, 23, 42, 0.75);
        border-radius: 8px;
        padding: 8px 10px;
        margin-top: 8px;
        line-height: 1.35;
    }
    .consult-swap-box {
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.25), rgba(15, 23, 42, 0.85));
        border: 1px dashed #38bdf8;
        border-radius: 8px;
        padding: 8px 10px;
        margin-top: 8px;
    }

    @media (max-width: 768px) {
        .main-header { font-size: 1.6rem; }
        .metric-value { font-size: 1.25rem; }
        .player-card, .live-card, .market-player-card { height: 260px; padding: 8px 4px; }
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

def render_market_player_card(p):
    """Renderiza card visual no mercado de atletas com tags inteligentes."""
    nome = p.get('Nome', 'Sem Nome')
    pos = p.get('Posicao', '')
    clube = p.get('Clube', '')
    preco = p.get('Preco', 0.0)
    media = p.get('Media', 0.0)
    xp = p.get('Media_Ajustada', 0.0)
    confronto = p.get('Confronto', '')
    tag = p.get('Tag', 'Boa Opção')
    tag_color = p.get('Tag_Color', '#f59e0b')
    just = p.get('Justificativa', '')
    sg_prob = p.get('SG_Prob', None)
    foto = p.get('Foto', '') or "https://s3.glbimg.com/v1/AUTH_58d78b787ec34892b5aaa0c7a146155f/clubes_2026/silhuetas/generica.png"
    escudo = p.get('Escudo', '')

    escudo_html = f'<img src="{escudo}" class="club-crest"/>' if escudo else ''
    sg_html = f'<span class="stat-badge badge-sg">🛡️ {sg_prob:.0f}%</span>' if (sg_prob is not None and pos in ['Goleiro', 'Lateral', 'Zagueiro']) else ''
    
    html = (
        f'<div class="market-player-card">'
        f'<div style="width:100%; display:flex; justify-content:space-between; align-items:center;">'
        f'<span class="market-tag" style="background:{tag_color}20; color:{tag_color}; border:1px solid {tag_color}40;">🏷️ {tag}</span>'
        f'<span class="stat-badge badge-pos" style="position:static;">{pos[:3].upper()}</span>'
        f'</div>'
        f'<div class="card-top">'
        f'<img src="{foto}" class="player-photo" onerror="this.src=\'https://s3.glbimg.com/v1/AUTH_58d78b787ec34892b5aaa0c7a146155f/clubes_2026/silhuetas/generica.png\';"/>'
        f'<div class="player-name" title="{nome}">{nome}</div>'
        f'<div class="player-club">{escudo_html}<span>{clube} • {confronto}</span></div>'
        f'</div>'
        f'<div style="margin:4px 0; display:flex; justify-content:center; gap:2px;">'
        f'<span class="stat-badge badge-price">C$ {preco:.2f}</span>'
        f'<span class="stat-badge badge-xp">⚡ {xp:.2f}</span>'
        f'{sg_html}'
        f'</div>'
        f'<div class="market-rationale" title="{just}">{just}</div>'
        f'</div>'
    )
    st.html(html)

def render_consult_player_card(s):
    """Renderiza card de diagnóstico individual do consultor tático."""
    nome = s.get('Nome', 'Sem Nome')
    pos = s.get('Posicao', '')
    clube = s.get('Clube', '')
    preco = s.get('Preco', 0.0)
    xp_final = s.get('xP_Final', 0.0)
    confronto = s.get('Confronto', '')
    is_cap = s.get('Is_Capitao', False)
    status_cons = s.get('Status_Consultoria', 'MANTER')
    just = s.get('Justificativa', '')
    sugestao = s.get('Sugestao_Troca')
    foto = s.get('Foto', '') or "https://s3.glbimg.com/v1/AUTH_58d78b787ec34892b5aaa0c7a146155f/clubes_2026/silhuetas/generica.png"
    escudo = s.get('Escudo', '')

    if status_cons == 'MANTER':
        badge_status_html = '<span class="consult-badge consult-badge-manter">✅ MANTER</span>'
        border_color = "#10b981"
    elif status_cons == 'ATENCAO':
        badge_status_html = '<span class="consult-badge consult-badge-atencao">⚠️ ATENÇÃO / APOSTA</span>'
        border_color = "#f59e0b"
    else:
        badge_status_html = '<span class="consult-badge consult-badge-trocar">❌ RECOMENDA TROCA</span>'
        border_color = "#ef4444"

    cap_html = '<span style="background:#f59e0b; color:#000; font-size:0.65rem; font-weight:800; padding:2px 6px; border-radius:4px; margin-right:4px;">👑 CAPITÃO (1.5x)</span>' if is_cap else ''
    escudo_html = f'<img src="{escudo}" class="club-crest"/>' if escudo else ''

    swap_html = ""
    if sugestao:
        gain_sign = "+" if sugestao['Delta_xP'] >= 0 else ""
        price_txt = f"(Economiza C$ {sugestao['Delta_Preco']:.2f})" if sugestao['Delta_Preco'] > 0 else f"(Custa +C$ {-sugestao['Delta_Preco']:.2f})" if sugestao['Delta_Preco'] < 0 else "(Mesmo preço)"
        swap_html = (
            f'<div class="consult-swap-box">'
            f'<div style="font-weight:800; font-size:0.75rem; color:#38bdf8; margin-bottom:2px;">🔄 Sugestão do Modelo:</div>'
            f'<div style="font-size:0.78rem; color:#f8fafc;">Substituir por <b>{sugestao["Nome"]}</b> ({sugestao["Clube"]} - C$ {sugestao["Preco"]:.2f})</div>'
            f'<div style="font-size:0.72rem; color:#34d399; font-weight:700; margin-top:2px;">{gain_sign}{sugestao["Delta_xP"]:.2f} pts esperados {price_txt}</div>'
            f'<div style="font-size:0.68rem; color:#94a3b8; margin-top:3px; font-style:italic;">{sugestao["Justificativa"]}</div>'
            f'</div>'
        )

    html = (
        f'<div class="consult-card" style="border-left: 4px solid {border_color};">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; width:100%; margin-bottom:6px;">'
        f'<div>{cap_html}<span style="font-size:0.70rem; font-weight:800; color:#94a3b8; text-transform:uppercase;">{pos}</span></div>'
        f'{badge_status_html}'
        f'</div>'
        f'<div style="display:flex; align-items:center; width:100%; gap:10px;">'
        f'<img src="{foto}" style="width:48px; height:48px; border-radius:50%; object-fit:cover; border:2px solid #475569;" onerror="this.src=\'https://s3.glbimg.com/v1/AUTH_58d78b787ec34892b5aaa0c7a146155f/clubes_2026/silhuetas/generica.png\';"/>'
        f'<div style="flex:1; text-align:left;">'
        f'<div style="font-weight:800; font-size:0.95rem; color:#f8fafc;">{nome}</div>'
        f'<div style="font-size:0.75rem; color:#94a3b8;">{escudo_html}{clube} • {confronto} • C$ {preco:.2f}</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:0.65rem; color:#94a3b8; font-weight:700;">PROJEÇÃO</div>'
        f'<div style="font-size:1.15rem; font-weight:900; color:#38bdf8;">{xp_final:.2f} pts</div>'
        f'</div>'
        f'</div>'
        f'<div class="consult-rationale">{just}</div>'
        f'{swap_html}'
        f'</div>'
    )
    st.html(html)

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
    """Renderiza um card visual de acompanhamento ao vivo com comparativo xP vs Real."""
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

    # Cálculo da Pontuação Esperada (xP)
    xp_expected = p.get('Media_Ajustada', 0.0) * (1.5 if is_captain else 1.0)

    if has_played:
        pts_bruto = float(pinfo.get('pontuacao', 0.0))
        pts_calc = pts_bruto * 1.5 if is_captain else pts_bruto
        pts_color = "#34d399" if pts_calc >= 0 else "#f87171"
        sub_txt = f'<div style="font-size:0.65rem;color:#f59e0b;">(Base: {pts_bruto:.2f} pts)</div>' if is_captain else ''
        
        # Comparativo: Desempenho Real vs. xP Projetado
        diff = pts_calc - xp_expected
        if diff > 0.5:
            perf_html = f'<div style="font-size:0.68rem;font-weight:800;color:#34d399;margin-top:2px;">🔥 +{diff:.2f} acima do xP ({xp_expected:.2f})</div>'
        elif diff < -0.5:
            perf_html = f'<div style="font-size:0.68rem;font-weight:800;color:#f87171;margin-top:2px;">❄️ {diff:.2f} abaixo do xP ({xp_expected:.2f})</div>'
        else:
            perf_html = f'<div style="font-size:0.68rem;font-weight:800;color:#fbbf24;margin-top:2px;">🎯 Na meta do xP ({xp_expected:.2f})</div>'

        score_box_html = (
            f'<div class="live-score-box">'
            f'<div class="live-score-val" style="color:{pts_color};">{pts_calc:+.2f} <span style="font-size:0.8rem;">pts</span></div>'
            f'{sub_txt}'
            f'{perf_html}'
            f'</div>'
        )
        
        # Scouts Chips
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
            f'<div style="font-size:0.68rem;font-weight:700;color:#38bdf8;margin-top:2px;">⚡ xP Projetado: {xp_expected:.2f} pts</div>'
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

    official_data = load_official_team()
    official_round = official_data.get('rodada', 25)

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
        
        # Seção 1: Modo de Operação com Rodada Dinâmica
        st.html('<div class="sidebar-section">📌 MODO DE OPERAÇÃO</div>')
        app_mode = st.radio(
            "Modo Selecionado:",
            options=["oficial", "simulador"],
            format_func=lambda x: f"🛡️ Time Oficial Escalado (Rodada {official_round})" if x == "oficial" else "🤖 Simulador / Novo Time",
            index=0,
            help=f"O modo 'Time Oficial' fixa a escalação real salva para a Rodada {official_round}. O modo 'Simulador' permite rodar o otimizador com novos valores e formações para qualquer rodada."
        )

        config_preview = load_config()
        default_budget = float(config_preview.get('defaults', {}).get('budget', 146.07))

        if app_mode == "simulador":
            # Seção 2: Cofre
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
            
            # Seção 3: Estratégia Tática
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
        else:
            budget = default_budget
            formation_option = "4-3-3"
            max_per_club = 5

        # Conexão com a API
        st.html('<div class="sidebar-section">🔄 ATUALIZAÇÃO DA API</div>')
        force_refresh = st.checkbox("Forçar atualização ao vivo da Globo", value=False)
        
        if app_mode == "simulador":
            st.markdown("")
            run_button = st.button("🚀 OTIMIZAR NOVO TIME", type="primary", use_container_width=True)
        
        # Placeholder para o botão de exportação na Sidebar
        export_sidebar_placeholder = st.sidebar.empty()
        
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
        official_starters_ids = official_data.get('starters_ids', [])
        official_captain_id = official_data.get('captain_id', 0)
        official_reserves_ids = official_data.get('reserves_ids', {})
        official_super_sub_pos = official_data.get('super_sub_pos', 'Atacante')
        
        target_ids = official_starters_ids + list(official_reserves_ids.values())
        
        with st.spinner("Processando dados dos atletas e confrontos..."):
            df = scorer.process_data(mercado_data, partidas_data, target_athlete_ids=target_ids)
            
            if df.empty:
                st.error("Nenhum atleta disponível para processamento.")
                return
                
            all_formations_summary = None
            
            if app_mode == "oficial":
                if str(rodada_num) != str(official_round) and rodada_num != '?':
                    st.warning(f"🔔 A Globo já abriu a **Rodada {rodada_num}**! Você está visualizando o time oficial salvo da **Rodada {official_round}**. Acesse o modo **Simulador** para escalar e salvar o time da Rodada {rodada_num}!")
                else:
                    st.success(f"🛡️ **Time Oficial do M1TOS EC (Rodada {official_round})** — Acompanhamento ao vivo sincronizado com a Globo.")
                    
                chosen_formation = "4-3-3"
                selected_df = df[df['ID'].isin(official_starters_ids)].copy()
                selected_df['Is_Capitao'] = (selected_df['ID'] == official_captain_id)
                
                # Montar reservas oficiais
                reservas = {}
                for pos, r_id in official_reserves_ids.items():
                    r_sub = df[df['ID'] == r_id]
                    if not r_sub.empty:
                        r_series = r_sub.iloc[0].copy()
                        worst_starter_xp = selected_df[selected_df['Posicao'] == pos]['Media_Ajustada'].min() if not selected_df[selected_df['Posicao'] == pos].empty else 0
                        r_series['Worst_Starter_XP'] = worst_starter_xp
                        r_series['Expected_Gain'] = round(max(0.0, (r_series.get('Upside', r_series.get('Media_Ajustada', 0)) - worst_starter_xp) * 0.4), 2)
                        reservas[pos] = r_series
            else:
                st.info(f"🏆 **Rodada {rodada_num} do Brasileirão** analisada no modo Simulador!")
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

        # 2. Alternador de Visualização Expandido
        tab_market, tab_consult, tab_cards, tab_live, tab_table, tab_comp = st.tabs([
            "🛒 Mercado & Tags",
            "🔍 Consultor Tático",
            "🏟️ Escalação Tática (Cards)", 
            "🔴 Parciais Ao Vivo", 
            "📊 Tabela Detalhada", 
            "📈 Comparativo de Formações"
        ])

        with tab_market:
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

            # Renderizar Grid do Mercado (4 por linha)
            grid_cols_num = 4
            m_list = m_df.to_dict('records')
            for i in range(0, len(m_list), grid_cols_num):
                row_athletes = m_list[i:i+grid_cols_num]
                cols = st.columns(len(row_athletes))
                for idx, ath in enumerate(row_athletes):
                    with cols[idx]:
                        render_market_player_card(ath)

        with tab_consult:
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

                # Ações Finais da Consultoria
                st.markdown("---")
                act_col1, act_col2 = st.columns([3, 2])
                with act_col1:
                    st.write("🛡️ **Pronto para a rodada?** Salve este time para travar sua escalação oficial e acompanhar parciais ao vivo.")
                with act_col2:
                    if st.button(f"💾 SALVAR COMO TIME OFICIAL (R{rodada_num})", type="primary", use_container_width=True, key="btn_save_advisor"):
                        res_ids = {pos: int(r['ID']) for pos, r in reservas.items()}
                        best_res_pos_calc = None
                        max_up = -1.0
                        for pos, r in reservas.items():
                            up = r.get('Upside', r.get('Media_Ajustada', 0))
                            if up > max_up:
                                max_up = up
                                best_res_pos_calc = pos
                                
                        save_official_team(
                            rodada=rodada_num,
                            starters_ids=selected_df['ID'].tolist(),
                            captain_id=int(capitao_row['ID']),
                            reserves_ids=res_ids,
                            super_sub_pos=best_res_pos_calc or "Atacante"
                        )
                        st.success(f"✅ Time da Rodada {rodada_num} salvo como Oficial com sucesso!")
                        st.rerun()

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

        # Relatório Unificado de Desempenho da Rodada (xP Projetado x Pontuação Real)
        st.markdown("---")
        
        report_rows = []
        for _, p in selected_df.iterrows():
            is_cap = (p['Nome'] == capitao_nome)
            xp_exp = p['Media_Ajustada'] * 1.5 if is_cap else p['Media_Ajustada']
            pinfo = pontuados.get(str(p.get('ID')))
            
            if pinfo is not None:
                pts_b = float(pinfo.get('pontuacao', 0.0))
                pts_r = pts_b * 1.5 if is_cap else pts_b
                diff_pts = round(pts_r - xp_exp, 2)
                if diff_pts > 0.5:
                    status_perf = "🔥 Superou xP"
                elif diff_pts < -0.5:
                    status_perf = "❄️ Ficou Abaixo"
                else:
                    status_perf = "🎯 Na Meta"
                scouts_d = ", ".join([f"{k}:{v}" for k, v in (pinfo.get('scout') or {}).items()])
            else:
                pts_r = None
                diff_pts = None
                status_perf = "⏳ Aguardando Jogo"
                scouts_d = "-"

            report_rows.append({
                "Tipo": "Titular",
                "Posição": p['Posicao'],
                "Jogador": f"👑 {p['Nome']} [C]" if is_cap else p['Nome'],
                "Clube": p['Clube'],
                "Preço (C$)": round(p['Preco'], 2),
                "xP Projetado": round(xp_exp, 2),
                "Pontos Reais": round(pts_r, 2) if pts_r is not None else "",
                "Saldo (Real - xP)": diff_pts if diff_pts is not None else "",
                "Desempenho": status_perf,
                "Scouts na Rodada": scouts_d
            })

        for pos, r in reservas.items():
            is_super = (pos == best_res_pos)
            xp_exp = r.get('Media_Ajustada', 0.0)
            rpinfo = pontuados.get(str(r.get('ID')))
            
            if rpinfo is not None:
                pts_r = float(rpinfo.get('pontuacao', 0.0))
                diff_pts = round(pts_r - xp_exp, 2)
                status_perf = "🔥 Superou xP" if diff_pts > 0.5 else ("❄️ Ficou Abaixo" if diff_pts < -0.5 else "🎯 Na Meta")
                scouts_d = ", ".join([f"{k}:{v}" for k, v in (rpinfo.get('scout') or {}).items()])
            else:
                pts_r = None
                diff_pts = None
                status_perf = "⏳ Aguardando Jogo"
                scouts_d = "-"

            nome_res_disp = f"⭐ {r['Nome']} [Reserva Luxo]" if is_super else r['Nome']
            report_rows.append({
                "Tipo": "Reserva",
                "Posição": r['Posicao'],
                "Jogador": nome_res_disp,
                "Clube": r['Clube'],
                "Preço (C$)": round(r['Preco'], 2),
                "xP Projetado": round(xp_exp, 2),
                "Pontos Reais": round(pts_r, 2) if pts_r is not None else "",
                "Saldo (Real - xP)": diff_pts if diff_pts is not None else "",
                "Desempenho": status_perf,
                "Scouts na Rodada": scouts_d
            })

        report_df = pd.DataFrame(report_rows)
        csv_report_data = report_df.to_csv(index=False).encode('utf-8-sig')

        # Renderizar Botão na Sidebar
        with export_sidebar_placeholder.container():
            st.html('<div class="sidebar-section">📊 EXPORTAR RELATÓRIO</div>')
            st.download_button(
                label="📥 Baixar Relatório (xP x Real)",
                data=csv_report_data,
                file_name=f"Relatorio_Desempenho_Rodada_{rodada_num}_M1TOS_EC.csv",
                mime="text/csv",
                type="secondary",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os dados: {e}")
        import traceback
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()

