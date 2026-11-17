"""Componentes visuais (cards e telas) do Cartola FC Optimizer Pro."""

import time
from datetime import datetime

import pandas as pd
import streamlit as st

from cartola_bot.auth_manager import AuthManager
from cartola_bot.gsheets_manager import save_official_team
from cartola_bot.lineup_service import sync_team_from_globo


def sync_team_from_globo_ui(api, token, rodada_num, mercado_data, partidas_data, scorer):
    """Wrapper de UI para sincronização com a Globo e atualização do session_state."""
    ok, msg, meta = sync_team_from_globo(api, token, rodada_num, mercado_data, partidas_data, scorer)
    if ok:
        for key in ("custom_starters_df", "custom_reserves", "custom_super_sub_pos"):
            if key in st.session_state:
                del st.session_state[key]
        if meta.get("patrimonio") is not None and st.session_state.get("cartola_session"):
            st.session_state["cartola_session"]["patrimonio"] = meta["patrimonio"]
    return ok, msg


def render_market_player_card(p):
    """Renderiza card visual no mercado de atletas com tags inteligentes."""
    nome = p.get('Nome', 'Sem Nome')
    pos = p.get('Posicao', '')
    clube = p.get('Clube', '')
    preco = p.get('Preco', 0.0)
    xp = p.get('Media_Ajustada', 0.0)
    confronto = p.get('Confronto', '')
    tag = p.get('Tag', 'Boa Opção')
    tag_color = p.get('Tag_Color', '#f59e0b')
    raw_just = p.get('Justificativa', '')
    just = "" if pd.isna(raw_just) or str(raw_just).lower() == 'nan' else str(raw_just)
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
    super_sub_html = '<div class="badge-captain" style="background:#10b981;color:#fff;font-size:0.8rem;padding:2px 6px;border-radius:6px;box-shadow:0 0 8px rgba(16,185,129,0.5);" title="Reserva de Luxo">⭐</div>' if is_super_sub else ''
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
    super_sub_html = '<div class="badge-captain" style="background:#10b981;color:#fff;font-size:0.8rem;padding:2px 6px;border-radius:6px;box-shadow:0 0 8px rgba(16,185,129,0.5);" title="Reserva de Luxo">⭐</div>' if is_super_sub else ''
    badge_html = super_sub_html if is_super_sub else captain_html
    escudo_html = f'<img src="{escudo}" class="club-crest"/>' if escudo else ''

    # Cálculo da Pontuação Esperada (xP) e Mínimo para Valorizar
    xp_expected = p.get('Media_Ajustada', 0.0) * (1.5 if is_captain else 1.0)
    preco_atleta = float(p.get('Preco', 10.0))
    min_val = float(p.get('Min_Val', preco_atleta * 0.37))

    if has_played:
        pts_bruto = float(pinfo.get('pontuacao', 0.0))
        pts_calc = pts_bruto * 1.5 if is_captain else pts_bruto
        pts_color = "#34d399" if pts_calc >= 0 else "#f87171"
        sub_txt = f'<div style="font-size:0.65rem;color:#f59e0b;">(Base: {pts_bruto:.2f} pts)</div>' if is_captain else ''

        # Comparativo: Desempenho Real vs. xP Projetado
        diff = pts_calc - xp_expected
        if diff > 0.5:
            perf_html = f'<div style="font-size:0.65rem;font-weight:800;color:#34d399;margin-top:2px;">🔥 +{diff:.2f} vs xP ({xp_expected:.1f})</div>'
        elif diff < -0.5:
            perf_html = f'<div style="font-size:0.65rem;font-weight:800;color:#f87171;margin-top:2px;">❄️ {diff:.2f} vs xP ({xp_expected:.1f})</div>'
        else:
            perf_html = f'<div style="font-size:0.65rem;font-weight:800;color:#fbbf24;margin-top:2px;">🎯 Na meta xP ({xp_expected:.1f})</div>'

        # Indicador de Valorização ao Vivo (Compacto)
        diff_val = pts_bruto - min_val
        if diff_val >= 0:
            val_html = f'<div style="font-size:0.65rem;font-weight:800;color:#34d399;margin-top:2px;background:rgba(52,211,153,0.12);padding:2px 4px;border-radius:4px;border:1px solid rgba(52,211,153,0.3);">📈 +{diff_val:.2f} (Mín {min_val:.1f})</div>'
        else:
            val_html = f'<div style="font-size:0.65rem;font-weight:800;color:#f87171;margin-top:2px;background:rgba(248,113,113,0.12);padding:2px 4px;border-radius:4px;border:1px solid rgba(248,113,113,0.3);">📉 -{abs(diff_val):.2f} (Mín {min_val:.1f})</div>'

        score_box_html = (
            f'<div class="live-score-box">'
            f'<div class="live-score-val" style="color:{pts_color};">{pts_calc:+.2f} <span style="font-size:0.8rem;">pts</span></div>'
            f'{sub_txt}'
            f'{perf_html}'
            f'{val_html}'
            f'</div>'
        )

        # Scouts Chips
        scouts_raw = pinfo.get('scout') or {}
        scout_chips = []
        if isinstance(scouts_raw, dict):
            scout_specs = [
                ("G", "scout-chip-g", "⚽", "G", True),
                ("A", "scout-chip-a", "🎯", "A", True),
                ("DS", "scout-chip-ds", "🛡️", "DS", True),
                ("DE", "scout-chip-de", "🧤", "DE", True),
                ("SG", "scout-chip-sg", "🛡️", "SG", False),
                ("FD", "scout-chip-a", "⚡", "FD", True),
                ("FF", "scout-chip-a", "👟", "FF", True),
                ("FT", "scout-chip-g", "🥅", "FT", True),
                ("FS", "scout-chip-ds", "🩹", "FS", True),
                ("CA", "scout-chip-ca", "🟨", "CA", True),
                ("CV", "scout-chip-cv", "🟥", "CV", True),
                ("FC", "scout-chip-cv", "⚠️", "FC", True),
                ("GS", "scout-chip-cv", "🥅", "GS", True),
                ("I", "scout-chip-ca", "🚩", "Imp", True),
                ("DP", "scout-chip-g", "🧤", "DP", True),
                ("PP", "scout-chip-cv", "❌", "PP", True),
                ("GC", "scout-chip-cv", "🚫", "GC", True),
                ("V", "scout-chip-g", "🏆", "Vit", False),
            ]
            for key, css_cls, icon, label, show_count in scout_specs:
                val = scouts_raw.get(key)
                if val:
                    text = f"{icon} {val}{label}" if show_count else f"{icon} {label}"
                    scout_chips.append(f'<span class="scout-chip {css_cls}">{text}</span>')

        chips_html = "".join(scout_chips) if scout_chips else '<span style="font-size:0.70rem;color:#94a3b8;">Em campo</span>'

    else:
        val_meta_html = f'<div style="font-size:0.65rem;font-weight:700;color:#38bdf8;margin-top:2px;">💵 Mínimo: {min_val:.2f} pts</div>'
        score_box_html = (
            f'<div class="live-score-box">'
            f'<div class="live-score-waiting">⏳ AGUARDANDO</div>'
            f'<div style="font-size:0.65rem;font-weight:700;color:#94a3b8;margin-top:2px;">⚡ xP: {xp_expected:.2f} pts</div>'
            f'{val_meta_html}'
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


def handle_globo_escalacao_result(success, resp_globo, rodada_num, selected_df, capitao_row, reservas, super_sub_pos="Atacante"):
    if success:
        st.balloons()
        st.success("🎉 **SUCESSO ABSOLUTO!** O time foi escalado diretamente na sua conta oficial do Cartola FC!")
        save_official_team(
            rodada=rodada_num,
            starters_df=selected_df,
            captain_id=int(capitao_row['ID']),
            reserves_dict=reservas,
            super_sub_pos=super_sub_pos
        )
        time.sleep(3.5)
        st.rerun()
    else:
        if "Expired" in str(resp_globo) or "não autorizado" in str(resp_globo) or "401" in str(resp_globo):
            st.error("❌ **Token da Globo Expirado:** A Globo invalida os tokens de autenticação a cada 60 minutos.")
            st.info("💡 **Como renovar em 10 segundos:**\n1. No navegador, acesse o Cartola e aperte **F12** -> aba **Rede**\n2. Copie o valor do cabeçalho **`Authorization`** (`Bearer eyJ...`)\n3. Cole no menu lateral em **'🔑 Renovar Token Globo'** e clique em **Atualizar Token**!")
        elif "cofre" in str(resp_globo).lower():
            team_cost = selected_df['Preco'].sum() if ('Preco' in selected_df.columns) else 0.0
            st.error("💰 **Saldo Insuficiente no Cartola (Cofre):**")
            st.warning(
                f"O Cartola FC recusou a escalação porque o custo total do time (**C$ {team_cost:.2f}**) ultrapassa o saldo de cartoletas disponível no seu cofre na conta oficial da Globo.\n\n"
                "👉 **Como resolver em 2 passos rápidos:**\n"
                "1. No menu lateral, acerte o campo **💰 Orçamento / Cofre (C$)** com o valor exato (ou um pouco abaixo) do seu patrimônio/saldo real no Cartola.\n"
                "2. Clique em **🚀 OTIMIZAR NOVO TIME** (ou substitua atletas caros) e tente clicar em **🚀 Escalar na Globo** novamente!"
            )
        else:
            st.error(f"❌ Erro ao enviar para o Cartola: {resp_globo}")


def render_login_screen():
    st.html('''
    <div style="max-width: 600px; margin: 30px auto 10px auto; padding: 32px 28px; background: linear-gradient(145deg, rgba(15,23,42,0.95), rgba(30,41,59,0.95)); border: 1px solid rgba(56,189,248,0.3); border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); text-align: center;">
        <div style="font-size: 3.5rem; margin-bottom: 8px;">🛡️⚽</div>
        <h1 style="font-size: 1.8rem; font-weight: 800; color: #f8fafc; margin: 0; background: linear-gradient(90deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">M1TOS EC • Cartola Pro</h1>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-top: 6px; margin-bottom: 20px;">Conecte seu token de autenticação oficial para escalação automática em 1 clique e gestão tática inteligente.</p>
    </div>
    ''')

    col_l, col_center, col_r = st.columns([1, 2.4, 1])
    with col_center:
        with st.container():
            st.markdown("### 🔑 Conexão via Token do Cartola FC")

            token_input = st.text_area(
                "Cole seu Bearer Token do Cartola FC:",
                placeholder="Exemplo: Bearer eyJhbGciOiJSUzI1NiIs...",
                height=110,
                key="gateway_token_input",
                help="Cole o token Bearer ou JWT oficial da sua conta do Cartola FC."
            )
            remember_session = st.checkbox(
                "💾 Salvar sessão de forma persistente (Google Sheets)",
                value=True,
                help="Mantém você conectado automaticamente nas próximas visitas sem precisar colar o token de novo."
            )

            if st.button("🚀 CONECTAR MEU TIME", type="primary", use_container_width=True, key="gateway_btn_do_token"):
                clean_tok = token_input.strip()
                if not clean_tok:
                    st.warning("⚠️ Cole o seu Bearer Token no campo acima para continuar.")
                else:
                    auth_header = clean_tok if clean_tok.startswith("Bearer ") else f"Bearer {clean_tok}"
                    with st.spinner("Validando token com a API do Cartola FC..."):
                        valid, team_info = AuthManager.validate_token(auth_header)
                        if valid:
                            team_name = team_info.get("nome", "M1TOS EC") if team_info else "M1TOS EC"
                            patrimonio = float(team_info.get("patrimonio", 136.94)) if team_info else 136.94
                            sess = {
                                "email": "usuario@cartola.pro",
                                "token": auth_header,
                                "glbid": auth_header.replace("Bearer ", ""),
                                "authenticated_at": datetime.now().isoformat(),
                                "team_name": team_name,
                                "nome_cartola": team_info.get("nome_cartola", "") if team_info else "",
                                "patrimonio": patrimonio,
                                "foto_perfil": team_info.get("foto_perfil", "") if team_info else "",
                                "url_escudo_svg": team_info.get("url_escudo_svg", "") if team_info else ""
                            }
                            AuthManager.save_session(sess, save_to_cloud=remember_session)
                            st.session_state["cartola_session"] = sess
                            st.session_state["cartola_token"] = auth_header
                            st.session_state["guest_mode"] = False
                            st.session_state["logged_out"] = False
                            st.balloons()
                            st.success(f"🎉 **Time Conectado com Sucesso!** Bem-vindo, **{team_name}** (C$ {patrimonio:.2f})!")
                            time.sleep(1.2)
                            st.rerun()
                        else:
                            st.error("❌ Token inválido ou expirado. Verifique se copiou o token completo que começa com 'Bearer eyJ...' ou 'eyJ...'")

            # Tutorial Passo a Passo Detalhado
            with st.expander("📖 Tutorial Rápido: Como pegar o seu Token em 20 segundos", expanded=True):
                st.markdown("""
                1. No seu computador, abra o site do Cartola: **[ge.globo.com/cartola](https://ge.globo.com/cartola/)**
                2. Verifique se o seu time já está aberto e logado na tela.
                3. Pressione a tecla **`F12`** no teclado *(ou clique com o botão direito e escolha "Inspecionar")*.
                4. Clique na aba **Rede** *(ou **Network**)* na janela que abrir.
                5. No campo de filtro (lupa), digite: **`time`**
                6. Pressione **`F5`** para atualizar a página.
                7. Clique na requisição chamada **`info`** ou **`time`** que aparecer na lista.
                8. Na aba **Headers** *(ou Cabeçalhos)* à direita, role até **Request Headers** *(Cabeçalhos da Solicitação)*.
                9. Copie o valor inteiro da linha **`Authorization:`** *(começa com `Bearer ey...`)* e cole aqui acima!
                """)

            st.markdown("---")
            if st.button("👀 Continuar como Visitante (Modo Apenas Consulta)", use_container_width=True, key="gateway_btn_guest"):
                st.session_state["guest_mode"] = True
                st.session_state["logged_out"] = False
                st.rerun()

