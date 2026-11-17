"""Estilização CSS customizada para o Cartola FC Optimizer Pro."""

import streamlit as st


def inject_custom_css() -> None:
    """Injeta os estilos CSS do dashboard e dos cards táticos."""
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
            padding: 10px 8px;
            text-align: center;
            position: relative;
            min-height: 315px;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-items: center;
            box-sizing: border-box;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            margin-bottom: 12px;
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
            border-radius: 8px;
            padding: 6px 8px;
            margin: 4px 0;
            width: 100%;
            box-sizing: border-box;
            text-align: center;
        }
        .live-score-val {
            font-size: 1.30rem;
            font-weight: 900;
            line-height: 1.2;
        }
        .live-score-waiting {
            font-size: 0.82rem;
            font-weight: 700;
            color: #94a3b8;
        }
        .live-scouts-container {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 2px;
            width: 100%;
            min-height: 22px;
            margin-top: 3px;
        }
        .scout-chip {
            font-size: 0.62rem;
            font-weight: 800;
            padding: 1px 4px;
            border-radius: 4px;
            background: #334155;
            color: #f1f5f9;
            display: inline-block;
            white-space: nowrap;
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
            min-height: 295px;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-items: center;
            box-sizing: border-box;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            margin-bottom: 12px;
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
            width: 100%;
            box-sizing: border-box;
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
            .player-card { min-height: 250px; padding: 6px 4px; }
            .live-card { min-height: 290px; padding: 6px 4px; }
            .market-player-card { min-height: 275px; padding: 6px 4px; }
            .player-photo { width: 46px; height: 46px; }
            .player-name { font-size: 0.78rem; }
            .live-score-val { font-size: 1.15rem; }
        }
    </style>
    """)
