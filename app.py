import json
import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from cartola_bot.api import CartolaAPI
from cartola_bot.auth_manager import AuthManager
from cartola_bot.scoring import Scorer
from cartola_bot.solver import TeamOptimizer
from cartola_bot.utils.config_loader import load_config

try:
    from cartola_bot.gsheets_manager import (
        HISTORICO_DIR,
        OFFICIAL_FILE,
        get_saved_rounds,
        has_gsheets_write_permission,
        is_gsheets_configured,
        load_official_team,
        save_official_team,
    )
except ImportError:
    from cartola_bot.gsheets_manager import (
        HISTORICO_DIR,
        OFFICIAL_FILE,
        get_saved_rounds,
        is_gsheets_configured,
        load_official_team,
        save_official_team,
    )
    def has_gsheets_write_permission():
        return False


from cartola_bot.backtesting import save_round_snapshot
from cartola_bot.lineup_service import validate_lineup_rules
from cartola_bot.notifier import (
    check_lineup_risks,
    minutes_until_close,
)
from ui.components import (
    handle_globo_escalacao_result,
    render_login_screen,
)
from ui.components import (
    sync_team_from_globo_ui as sync_team_from_globo,
)
from ui.styles import inject_custom_css
from ui.tabs.backtest import render_backtest_tab
from ui.tabs.cards import render_cards_tab
from ui.tabs.comparison import render_comparison_tab
from ui.tabs.consult import render_consult_tab
from ui.tabs.live import render_live_tab
from ui.tabs.market import render_market_tab
from ui.tabs.table import render_table_tab

# Configuração da página para máxima responsividade
st.set_page_config(
    page_title="Cartola FC Optimizer Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="auto"
)


inject_custom_css()

@st.cache_data(ttl=600)
def load_app_data(use_cache=True):
    """Carrega dados da API e inicializa os módulos."""
    config = load_config()
    api = CartolaAPI(config)
    mercado_data = api.get_mercado(use_cache=use_cache)
    partidas_data = api.get_partidas(use_cache=use_cache)
    save_round_snapshot(
        rodada=partidas_data.get("rodada"),
        mercado_data=mercado_data,
        partidas_data=partidas_data,
    )
    return config, mercado_data, partidas_data


def main():
    is_guest = st.session_state.get("guest_mode", False)
    is_logged_out = st.session_state.get("logged_out", False)

    # Se o usuário fez logout explícito, não recupera automaticamente da nuvem/secrets
    if is_logged_out:
        session_data = None
        st.session_state["cartola_session"] = None
        st.session_state["cartola_token"] = ""
        has_active_auth = False
    else:
        # 1. Checar Sessão de Autenticação Ativa
        session_data = st.session_state.get("cartola_session")
        if not session_data:
            session_data = AuthManager.load_active_session()
            if session_data:
                st.session_state["cartola_session"] = session_data
                st.session_state["cartola_token"] = session_data.get("token", "")

        has_active_auth = bool(session_data or st.session_state.get("cartola_token"))

    # Se não houver autenticação e não estiver em modo visitante, exibe a tela de login como porta de entrada
    if not has_active_auth and not is_guest:
        render_login_screen()
        return

    st.html('<div class="main-header">🛡️ M1TOS EC • Cartola Pro</div><div class="sub-header">Otimizador Tático Inteligente com Pontuação Esperada (xP) & Reserva de Luxo</div>')

    saved_rounds = get_saved_rounds()
    official_data = load_official_team()
    official_round = official_data.get('rodada', 25)

    with st.sidebar:
        active_token = st.session_state.get("cartola_token", "")
        team_name_disp = "M1TOS EC"
        patrimonio_real = 141.66

        if session_data:
            team_name_disp = session_data.get("team_name", "M1TOS EC")
            patrimonio_real = float(session_data.get("patrimonio", 141.66))
            active_token = session_data.get("token", active_token)

        if active_token:
            try:
                temp_api = CartolaAPI(load_config())
                user_glb_team = temp_api.get_user_team(active_token)
                if user_glb_team:
                    glb_pat = user_glb_team.get('patrimonio') or user_glb_team.get('time', {}).get('patrimonio') or user_glb_team.get('patrimonio_num')
                    if glb_pat is not None:
                        patrimonio_real = float(glb_pat)
                        if session_data:
                            session_data["patrimonio"] = patrimonio_real
                    glb_nome = user_glb_team.get('time', {}).get('nome') or user_glb_team.get('nome')
                    if glb_nome:
                        team_name_disp = glb_nome
                        if session_data:
                            session_data["team_name"] = team_name_disp
            except Exception:
                pass

        if patrimonio_real == 141.66:
            try:
                temp_api = CartolaAPI(load_config())
                pub_team = temp_api.get_public_team(142227)
                if pub_team and 'patrimonio' in pub_team:
                    patrimonio_real = float(pub_team['patrimonio'])
                    if session_data:
                        session_data["patrimonio"] = patrimonio_real
                if pub_team and 'time' in pub_team and 'nome' in pub_team['time']:
                    team_name_disp = pub_team['time']['nome']
            except Exception:
                pass

        # Card do Perfil do Time
        status_color = "#38bdf8" if active_token else "#f59e0b"
        status_text = "🟢 CONECTADO À GLOBO" if active_token else "🟡 MODO CONSULTA"

        st.html(f'''
        <div class="team-profile-card">
            <div class="team-shield">🏆</div>
            <div class="team-title">{team_name_disp}</div>
            <div class="team-subtitle">Cartola FC • Temporada 2026</div>
            <div class="market-status-pill" style="background:rgba(56,189,248,0.15);color:{status_color};border:1px solid rgba(56,189,248,0.3);">💰 PATRIMÔNIO: C$ {patrimonio_real:.2f}</div>
            <div style="font-size:0.75rem; color:{status_color}; margin-top:5px; font-weight:600; text-align:center;">{status_text}</div>
        </div>
        ''')

        if active_token:
            if st.button("📥 Sincronizar com a Globo", use_container_width=True, key="btn_sync_sidebar", help="Importa e sincroniza a escalação atual salva no Cartola FC"):
                st.session_state["trigger_sync_globo"] = True
                st.rerun()
            if st.button("🚪 Sair / Desconectar Conta", use_container_width=True, key="btn_logout_sidebar"):
                AuthManager.logout()
                st.session_state["cartola_session"] = None
                st.session_state["cartola_token"] = ""
                st.session_state["logged_out"] = True
                st.session_state["guest_mode"] = False
                st.rerun()
        else:
            if st.button("🔐 Conectar Conta Globo", type="primary", use_container_width=True, key="btn_login_sidebar"):
                st.session_state["guest_mode"] = False
                st.session_state["logged_out"] = False
                st.rerun()

        with st.sidebar.expander("🔑 Renovar Token da Globo", expanded=False):
            st.caption("Atualize ou troque seu token sem precisar sair da conta:")
            token_in = st.text_area("Novo Bearer Token:", height=90, key="sidebar_token_renewal_input", placeholder="Bearer eyJ...")
            if st.button("🔄 Validar e Salvar Novo Token", use_container_width=True, key="btn_apply_token"):
                clean_in = token_in.strip()
                if not clean_in:
                    st.warning("⚠️ Cole o token antes de atualizar.")
                else:
                    auth_in = clean_in if clean_in.startswith("Bearer ") else f"Bearer {clean_in}"
                    valid_t, team_t = AuthManager.validate_token(auth_in)
                    if valid_t:
                        new_team_name = team_t.get("nome", team_name_disp) if team_t else team_name_disp
                        new_patrimonio = float(team_t.get("patrimonio", patrimonio_real)) if team_t else patrimonio_real
                        sess_update = {
                            "email": session_data.get("email", "usuario@cartola.pro") if session_data else "usuario@cartola.pro",
                            "token": auth_in,
                            "glbid": auth_in.replace("Bearer ", ""),
                            "authenticated_at": datetime.now().isoformat(),
                            "team_name": new_team_name,
                            "patrimonio": new_patrimonio
                        }
                        AuthManager.save_session(sess_update, save_to_cloud=True)
                        st.session_state["cartola_session"] = sess_update
                        st.session_state["cartola_token"] = auth_in
                        st.session_state["logged_out"] = False
                        st.success(f"✅ Token renovado com sucesso para **{new_team_name}**!")
                        time.sleep(1.2)
                        st.rerun()
                    else:
                        st.error("❌ Token inválido ou expirado. Tente novamente.")

        # Seção 1: Modo de Operação com Rodada Dinâmica e Histórico
        st.html('<div class="sidebar-section">📌 MODO DE OPERAÇÃO</div>')
        app_mode = st.radio(
            "Modo Selecionado:",
            options=["oficial", "simulador"],
            format_func=lambda x: f"🛡️ Time Oficial Salvo (Rodada {official_round})" if x == "oficial" else "🤖 Simulador / Novo Time",
            index=0,
            help=f"O modo 'Time Oficial' fixa a escalação real e imutável da Rodada {official_round}. O modo 'Simulador' permite rodar o otimizador para qualquer rodada ativa."
        )

        if len(saved_rounds) > 1 and app_mode == "oficial":
            selected_history_round = st.selectbox("Consultar Rodada Histórica:", saved_rounds, index=0)
            if selected_history_round != official_round:
                official_data = load_official_team(rodada=selected_history_round)
                official_round = selected_history_round

        budget = float(patrimonio_real)

        if app_mode == "simulador":
            # Seção 2: Estratégia Tática
            st.html('<div class="sidebar-section">📋 ESTRATÉGIA TÁTICA</div>')
            budget = st.number_input(
                "💰 Orçamento / Cofre (C$):",
                min_value=40.0,
                max_value=500.0,
                value=round(float(patrimonio_real), 2),
                step=1.0,
                help="Valor máximo em cartoletas para montar o time. O Cartola FC rejeitará escalações que custem mais que o saldo disponível no seu cofre."
            )
            config_preview = load_config()
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

            avoid_conflict = st.checkbox(
                "🛡️ Evitar Ataque vs Defesa (Proteção SG)",
                value=config_preview.get('defaults', {}).get('avoid_attack_vs_defense_conflict', True),
                help="Impede a escalação de atacantes ou meias contra os defensores escalados no mesmo confronto, eliminando canibalização de SG."
            )

            # Reset automático de modificações manuais caso mude de tática ou orçamento
            last_b = st.session_state.get("last_tactical_budget")
            last_f = st.session_state.get("last_tactical_formation")
            if (last_b is not None and abs(last_b - budget) > 0.01) or (last_f is not None and last_f != formation_option):
                for k in ["custom_starters_df", "custom_reserves", "custom_super_sub_pos", "select_captain_change"]:
                    st.session_state.pop(k, None)
            st.session_state["last_tactical_budget"] = budget
            st.session_state["last_tactical_formation"] = formation_option
        else:
            budget = float(official_data.get('total_cost', patrimonio_real))
            formation_option = "4-3-3"
            max_per_club = 5
            avoid_conflict = True

        # Conexão com a API
        st.html('<div class="sidebar-section">🔄 ATUALIZAÇÃO DA API</div>')
        force_refresh = st.checkbox("Forçar atualização ao vivo da Globo", value=False)

        if app_mode == "simulador":
            st.markdown("")
            if st.button("🚀 OTIMIZAR NOVO TIME", type="primary", use_container_width=True, key="btn_run_optimizer"):
                for k in ["custom_starters_df", "custom_reserves", "custom_super_sub_pos", "select_captain_change"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()


        # Placeholder para o botão de exportação na Sidebar
        export_sidebar_placeholder = st.sidebar.empty()

        # Seção de Sincronização em Nuvem & Backup
        st.html('<div class="sidebar-section">☁️ SINCRONIZAÇÃO EM NUVEM</div>')
        if is_gsheets_configured():
            if has_gsheets_write_permission():
                st.success("🟢 Google Sheets Conectado (CRUD)", icon="☁️")
            else:
                st.info("🟡 Google Sheets Conectado (Leitura)", icon="☁️")
        else:
            st.info("🟡 Armazenamento Local Ativo", icon="💾")
            with st.expander("ℹ️ Como ligar Google Sheets"):
                st.markdown("""
                **Para salvar na nuvem:**
                1. Conecte sua planilha Google no Streamlit Secrets (`[connections.gsheets]`).
                2. Cada time salvo será gravado instantaneamente na sua planilha do Google Drive.
                """)

        with st.expander("📥 Backup & Restauração (.json)"):
            curr_team_json = json.dumps(official_data, indent=2, ensure_ascii=False)
            st.download_button(
                label=f"💾 Baixar Escalação R{official_round} (.json)",
                data=curr_team_json,
                file_name=f"escalacao_m1tos_rodada_{official_round}.json",
                mime="application/json",
                use_container_width=True
            )
            uploaded_json = st.file_uploader("Restaurar arquivo .json:", type=["json"], key="upload_backup_team")
            if uploaded_json is not None:
                try:
                    restored_data = json.load(uploaded_json)
                    if "rodada" in restored_data and ("starters_ids" in restored_data or "starters" in restored_data):
                        r_num = restored_data["rodada"]
                        os.makedirs(HISTORICO_DIR, exist_ok=True)
                        with open(os.path.join(HISTORICO_DIR, f"rodada_{r_num}.json"), 'w', encoding='utf-8') as f:
                            json.dump(restored_data, f, indent=2, ensure_ascii=False)
                        with open(OFFICIAL_FILE, 'w', encoding='utf-8') as f:
                            json.dump(restored_data, f, indent=2, ensure_ascii=False)
                        st.success(f"✅ Escalação da Rodada {r_num} restaurada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Arquivo JSON inválido para escalação.")
                except Exception as e:
                    st.error(f"Erro ao ler arquivo: {e}")

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

        rodada_num = partidas_data.get('rodada', '?')
        official_starters_ids = official_data.get('starters_ids', [])
        official_captain_id = official_data.get('captain_id', 0)
        official_reserves_ids = official_data.get('reserves_ids', {})
        official_super_sub_pos = official_data.get('super_sub_pos', 'Atacante')

        # Se foi disparada sincronização com a Globo pelo menu lateral
        if st.session_state.get("trigger_sync_globo"):
            st.session_state["trigger_sync_globo"] = False
            token_to_use = active_token or (st.secrets.get("cartola_token", "") if hasattr(st, "secrets") else "")
            with st.spinner("📥 Sincronizando escalação diretamente da Globo..."):
                sync_ok, sync_msg = sync_team_from_globo(api, token_to_use, rodada_num, mercado_data, partidas_data, scorer)
                if sync_ok:
                    st.success(f"✅ {sync_msg}")
                    time.sleep(1.2)
                    st.rerun()
                else:
                    st.error(f"❌ {sync_msg}")

        target_ids = (official_starters_ids + list(official_reserves_ids.values())) if app_mode == "oficial" else None
        with st.spinner("Processando dados dos atletas e confrontos..."):
            df = scorer.process_data(mercado_data, partidas_data, target_athlete_ids=target_ids)

            if df.empty:
                st.error("Nenhum atleta disponível para processamento.")
                return

            all_formations_summary = None

            if app_mode == "oficial":
                if str(rodada_num) != str(official_round) and rodada_num != '?':
                    st.info(f"📜 **Histórico / Time Oficial (Rodada {official_round})** — A Globo já abriu a **Rodada {rodada_num}**. Acesse o **Simulador** quando quiser escalar o novo time!")
                else:
                    st.success(f"🛡️ **Time Oficial do M1TOS EC (Rodada {official_round})** — Acompanhamento ao vivo sincronizado com a Globo.")

                chosen_formation = "4-3-3"

                # Se houver snapshot congelado com preços e xP originais, usa diretamente
                if official_data.get('starters'):
                    selected_df = pd.DataFrame(official_data['starters'])
                    reservas = {pos: pd.Series(r) for pos, r in official_data.get('reserves', {}).items()}
                else:
                    selected_df = df[df['ID'].isin(official_starters_ids)].copy()
                    selected_df['Is_Capitao'] = (selected_df['ID'] == official_captain_id)
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
                optimizer.avoid_attack_vs_defense_conflict = avoid_conflict
                if formation_option == "auto":
                    try:
                        chosen_formation, selected_df, best_score, all_formations_summary = optimizer.optimize_best_formation(
                            df, budget=budget, max_players_per_club=max_per_club,
                            avoid_attack_vs_defense_conflict=avoid_conflict
                        )
                    except TypeError:
                        chosen_formation, selected_df, best_score, all_formations_summary = optimizer.optimize_best_formation(
                            df, budget=budget, max_players_per_club=max_per_club
                        )
                else:
                    chosen_formation = formation_option
                    try:
                        selected_df = optimizer.optimize(
                            df, budget=budget, formation_name=chosen_formation, max_players_per_club=max_per_club,
                            avoid_attack_vs_defense_conflict=avoid_conflict
                        )
                    except TypeError:
                        selected_df = optimizer.optimize(
                            df, budget=budget, formation_name=chosen_formation, max_players_per_club=max_per_club
                        )

                if selected_df is None or selected_df.empty:
                    st.error("Não foi possível montar um time completo com esse orçamento. Tente aumentar o valor em cartoletas.")
                    return

                reservas = optimizer.get_reservas(df, selected_df)

            # Verificar se o usuário fez substituições personalizadas manuais na sessão
            if "custom_starters_df" in st.session_state and st.session_state.get("custom_mode_owner") == app_mode:
                selected_df = st.session_state["custom_starters_df"]
                reservas = optimizer.get_reservas(df, selected_df)

        reservas = reservas or {}
        if "custom_reserves" in st.session_state and st.session_state.get("custom_mode_owner") == app_mode:
            reservas = dict(reservas)
            for pos_name, r_cand in st.session_state["custom_reserves"].items():
                reservas[pos_name] = r_cand

        capitao_row = selected_df[selected_df['Is_Capitao']].iloc[0] if 'Is_Capitao' in selected_df.columns and selected_df['Is_Capitao'].any() else selected_df.iloc[0]
        capitao_nome = capitao_row['Nome']
        capitao_extra = capitao_row['Media_Ajustada'] * 0.5
        total_xp = selected_df['Media_Ajustada'].sum() + capitao_extra
        total_cost = selected_df['Preco'].sum()
        budget_left = budget - total_cost

        # Controles Rápidos: Capitão, Reserva de Luxo & Reset de Modificações
        with st.container():
            ctrl_c1, ctrl_c2, ctrl_c3 = st.columns([3, 3, 2])
            with ctrl_c1:
                current_cap = selected_df[selected_df['Is_Capitao']]['Nome'].values[0] if 'Is_Capitao' in selected_df.columns and selected_df['Is_Capitao'].any() else selected_df.iloc[0]['Nome']
                cap_options = selected_df['Nome'].tolist()
                cap_idx = cap_options.index(current_cap) if current_cap in cap_options else 0
                new_cap_name = st.selectbox("👑 Capitão (1.5x Pontos):", options=cap_options, index=cap_idx)
                if new_cap_name != current_cap:
                    updated_df = selected_df.copy()
                    updated_df['Is_Capitao'] = (updated_df['Nome'] == new_cap_name)
                    st.session_state["custom_starters_df"] = updated_df
                    st.session_state["custom_mode_owner"] = app_mode
                    st.rerun()

            with ctrl_c2:
                if reservas:
                    all_reservas = {k: v for k, v in reservas.items() if hasattr(v, 'get')}
                    sub_res_names = [f"{r.get('Nome')} ({pos} - {r.get('Clube')})" for pos, r in all_reservas.items()]
                    sub_res_keys = list(all_reservas.keys())
                    super_sub_pos_chosen = st.session_state.get("custom_super_sub_pos", official_super_sub_pos or "Atacante")
                    if super_sub_pos_chosen not in sub_res_keys:
                        super_sub_pos_chosen = "Atacante" if "Atacante" in sub_res_keys else (sub_res_keys[0] if sub_res_keys else "Meia")
                    curr_res_idx = sub_res_keys.index(super_sub_pos_chosen) if super_sub_pos_chosen in sub_res_keys else 0
                    chosen_res_label = st.selectbox("⭐ Reserva de Luxo (Banco):", options=sub_res_names, index=curr_res_idx)
                    chosen_idx = sub_res_names.index(chosen_res_label)
                    chosen_pos = sub_res_keys[chosen_idx]
                    if chosen_pos != super_sub_pos_chosen:
                        st.session_state["custom_super_sub_pos"] = chosen_pos
                        st.rerun()

            with ctrl_c3:
                st.write("")
                st.write("")
                if "custom_starters_df" in st.session_state or "custom_super_sub_pos" in st.session_state or "custom_reserves" in st.session_state:
                    if st.button("⏪ Resetar Modificações", use_container_width=True, key="btn_reset_custom_team"):
                        for k in ["custom_starters_df", "custom_reserves", "custom_super_sub_pos", "select_captain_change"]:
                            if k in st.session_state:
                                del st.session_state[k]
                        st.rerun()

        # Determinar super_sub ativo
        super_sub_pos_chosen = st.session_state.get("custom_super_sub_pos", official_super_sub_pos or "Atacante")
        super_sub_id = None
        super_sub_name = ""
        if reservas:
            if super_sub_pos_chosen not in reservas:
                # Priorizar ofensivos (Atacante > Meia) ou maior upside geral
                preferred_order = ['Atacante', 'Meia', 'Lateral', 'Zagueiro', 'Goleiro']
                super_sub_pos_chosen = next((p for p in preferred_order if p in reservas), list(reservas.keys())[0])
            if super_sub_pos_chosen in reservas:
                r_active = reservas[super_sub_pos_chosen]
                super_sub_id = r_active.get('ID') if hasattr(r_active, 'get') else None
                super_sub_name = r_active.get('Nome') if hasattr(r_active, 'get') else ""

        # 1. Cards de Resumo no Topo
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.html(f'<div class="metric-card"><div class="metric-title">🚀 Pontuação Esperada</div><div class="metric-value">{total_xp:.2f} pts</div></div>')
        with c2:
            st.html(f'<div class="metric-card"><div class="metric-title">💎 Custo dos Titulares</div><div class="metric-value">C$ {total_cost:.2f}</div></div>')
        with c3:
            if budget_left < 0:
                st.html(f'<div class="metric-card" style="border:1px solid #ef4444;"><div class="metric-title" style="color:#ef4444;">⚠️ Saldo Estourado</div><div class="metric-value" style="color:#ef4444;">C$ {budget_left:.2f}</div></div>')
            else:
                st.html(f'<div class="metric-card"><div class="metric-title">🏦 Sobra no Caixa</div><div class="metric-value">C$ {budget_left:.2f}</div></div>')
        with c4:
            st.html(f'<div class="metric-card"><div class="metric-title">📋 Formação Tática</div><div class="metric-value">{chosen_formation}</div></div>')

        if active_token and total_cost > patrimonio_real:
            st.warning(f"⚠️ **Atenção ao Cofre:** O custo dos titulares (**C$ {total_cost:.2f}**) ultrapassa o patrimônio da sua conta Globo (**C$ {patrimonio_real:.2f}**). Ajuste o **Orçamento (C$)** na barra lateral e reotimize para que a compra seja aceita pelo Cartola FC.")

        # Monitor Automático de Alterações de Última Hora (direto no Dashboard)
        current_team_payload = {
            "starters": selected_df.to_dict(orient="records"),
            "reserves": {
                pos: (dict(r) if hasattr(r, "items") else {})
                for pos, r in (reservas or {}).items()
            },
        }
        lineup_risks = check_lineup_risks(current_team_payload, mercado_data)
        if lineup_risks:
            mercado_status = api.get_mercado_status()
            mins_left = minutes_until_close(mercado_status)
            tempo_badge = f" • ⏰ Mercado fecha em **{int(mins_left)} min**" if mins_left is not None else ""
            risk_lines = "\n".join(
                f"- **[{r['role']}] {r['nome']}** ({r['clube']} - {r['posicao']}): `{r['status_nome']}`"
                for r in lineup_risks
            )
            st.error(
                f"🚨 **Alteração de Última Hora Detectada ({len(lineup_risks)} atleta(s) fora de 'Provável')**{tempo_badge}\n\n"
                f"{risk_lines}"
            )
            if st.button("🔄 Atualizar Mercado", key="btn_refresh_market_risk"):
                st.cache_data.clear()
                st.rerun()

        # Banner de Ação Principal (Escalar no Cartola / Salvar)
        st.markdown("")
        banner_c1, banner_c2 = st.columns([2.8, 2.7])
        with banner_c1:
            super_sub_badge_txt = f" | ⭐ Reserva de Luxo: **{super_sub_name} ({super_sub_pos_chosen})**" if super_sub_name else ""
            st.markdown(f"🛡️ **Time M1TOS EC • Rodada {rodada_num}** | Projeção: **{total_xp:.2f} pts** | Custo: **C$ {total_cost:.2f}** | Capitão: **👑 {capitao_nome}**{super_sub_badge_txt}")
        with banner_c2:
            act_b1, act_b2, act_b3 = st.columns(3)
            with act_b1:
                if st.button("💾 Salvar Oficial", use_container_width=True, key="btn_main_save_banner"):
                    save_official_team(
                        rodada=rodada_num,
                        starters_df=selected_df,
                        captain_id=int(capitao_row['ID']),
                        reserves_dict=reservas,
                        super_sub_pos=super_sub_pos_chosen or "Atacante"
                    )
                    st.success(f"✅ Time da Rodada {rodada_num} salvo como Oficial!")
                    st.rerun()
            with act_b2:
                if st.button("🚀 Escalar na Globo", type="primary", use_container_width=True, key="btn_main_autoscale_banner"):
                    valid_lineup, val_errors = validate_lineup_rules(selected_df, reservas)
                    if not valid_lineup:
                        for err in val_errors:
                            st.error(f"❌ {err}")
                    else:
                        with st.spinner("Enviando escalação diretamente para a Globo..."):
                            token_to_use = active_token or (st.secrets.get("cartola_token", "") if hasattr(st, "secrets") else "")
                            if not token_to_use:
                                st.warning("⚠️ Você precisa conectar sua conta Globo no menu lateral para enviar diretamente para a API.")
                            else:
                                success, resp_globo = api.save_time_to_globo(
                                    token=token_to_use,
                                    esquema_name=chosen_formation,
                                    captain_id=int(capitao_row['ID']),
                                    starters_ids=selected_df['ID'].tolist(),
                                    reserves_dict=reservas,
                                    super_sub_id=super_sub_id
                                )
                                handle_globo_escalacao_result(success, resp_globo, rodada_num, selected_df, capitao_row, reservas, super_sub_pos=super_sub_pos_chosen)
            with act_b3:
                if st.button("📥 Puxar da Globo", use_container_width=True, key="btn_main_sync_banner", help="Importa as alterações e escalação salvas no app do Cartola FC"):
                    with st.spinner("📥 Sincronizando time direto da sua conta Globo..."):
                        token_to_use = active_token or (st.secrets.get("cartola_token", "") if hasattr(st, "secrets") else "")
                        sync_ok, sync_msg = sync_team_from_globo(api, token_to_use, rodada_num, mercado_data, partidas_data, scorer)
                        if sync_ok:
                            st.success(f"✅ {sync_msg}")
                            time.sleep(1.2)
                            st.rerun()
                        else:
                            st.error(f"❌ {sync_msg}")

        # 2. Alternador de Visualização Expandido
        tab_market, tab_consult, tab_cards, tab_live, tab_table, tab_comp, tab_backtest = st.tabs([
            "🛒 Mercado & Tags",
            "🔍 Consultor Tático",
            "🏟️ Escalação Tática (Cards)",
            "🔴 Parciais Ao Vivo",
            "📊 Tabela Detalhada",
            "📈 Comparativo de Formações",
            "🧪 Backtesting & Calibração",
        ])

        with tab_market:
            render_market_tab(df, selected_df, rodada_num, app_mode)

        with tab_consult:
            render_consult_tab(
                df, selected_df, reservas, capitao_row, chosen_formation,
                super_sub_id, super_sub_pos_chosen, rodada_num, budget, app_mode,
                active_token, api, scorer, optimizer, mercado_data, partidas_data,
            )

        with tab_cards:
            render_cards_tab(
                df, selected_df, reservas, capitao_row, capitao_nome, chosen_formation,
                super_sub_id, super_sub_pos_chosen, rodada_num, app_mode,
                active_token, api, scorer, mercado_data, partidas_data,
            )

        with tab_live:
            pontuados, best_res_pos = render_live_tab(
                selected_df, reservas, capitao_nome, super_sub_pos_chosen,
                rodada_num, official_round, app_mode, api,
            )

        with tab_table:
            render_table_tab(selected_df, capitao_nome)

        with tab_comp:
            render_comparison_tab(
                df, rodada_num, budget, max_per_club, chosen_formation,
                all_formations_summary, optimizer,
            )

        with tab_backtest:
            render_backtest_tab(config)

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

        if reservas:
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

