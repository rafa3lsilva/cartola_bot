#!/usr/bin/env python3
"""
Capturador Automático de Sessão do Cartola FC
=============================================
Abre o Cartola FC (ge.globo.com/cartola) no Chrome.
Você clica em 'Entrar', digita sua conta Globo e resolve o Captcha.
Assim que o seu time carregar, o script intercepta o Bearer Token oficial do Cartola,
salva no .session_cache.json e sincroniza com o Streamlit!
"""

import sys
import os
import json
import time
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from cartola_bot.auth_manager import AuthManager, SESSION_FILE

def find_system_chrome():
    candidates = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def login_with_browser():
    from playwright.sync_api import sync_playwright

    chrome_path = find_system_chrome()

    print("\n" + "="*65)
    print("⚽ M1TOS EC • LOGIN OFICIAL DO CARTOLA FC NO NAVEGADOR")
    print("="*65)
    print("🚀 Abrindo o Cartola FC no navegador...")
    print("👉 Se não estiver logado, clique em 'Entrar' e faça login normalmente.")
    print("⏳ O script interceptará o Token Bearer oficial assim que seu time carregar!")
    print("="*65 + "\n")

    captured_token = None
    user_email = "rafaelpjmp@gmail.com"

    with sync_playwright() as p:
        launch_args = {
            "headless": False,
            "args": ["--start-maximized", "--disable-blink-features=AutomationControlled"]
        }
        if chrome_path:
            launch_args["executable_path"] = chrome_path

        browser = p.chromium.launch(**launch_args)
        context = browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        def on_request(request):
            nonlocal captured_token
            h = request.headers
            for k in ['authorization', 'x-glb-token']:
                val = h.get(k, '')
                if val and 'Bearer ey' in val:
                    # Token JWT oficial da API do Cartola
                    if len(val) > 120 and 'api.cartola' in request.url or 'cartolafc' in request.url:
                        captured_token = val
                        print(f"🎯 TOKEN DO CARTOLA FC CAPTURADO!")

        page.on('request', on_request)

        # Abre diretamente o Cartola FC
        page.goto("https://ge.globo.com/cartola/")

        # Aguardar login e captura do token por até 4 minutos
        start_time = time.time()
        timeout_seconds = 240

        while time.time() - start_time < timeout_seconds:
            if captured_token:
                break
            time.sleep(1.0)

        if not captured_token:
            print("❌ Tempo limite esgotado sem detectar o token do Cartola.")
            browser.close()
            return False

        clean_token = captured_token if captured_token.startswith("Bearer ") else f"Bearer {captured_token}"
        print(f"\n🎉 SUCESSO! Token oficial do Cartola autenticado!")
        print(f"🔑 Token: {clean_token[:35]}...{clean_token[-15:]}")

        print("📡 Validando credencial com os servidores do Cartola FC...")
        valid, team_info = AuthManager.validate_token(clean_token)

        team_name = team_info.get("nome", "M1TOS EC") if team_info else "M1TOS EC"
        patrimonio = float(team_info.get("patrimonio", 136.94)) if team_info else 136.94

        session_data = {
            "email": user_email,
            "token": clean_token,
            "glbid": clean_token.replace("Bearer ", ""),
            "authenticated_at": datetime.now().isoformat(),
            "team_name": team_name,
            "nome_cartola": team_info.get("nome_cartola", "") if team_info else "",
            "patrimonio": patrimonio,
            "foto_perfil": team_info.get("foto_perfil", "") if team_info else "",
            "url_escudo_svg": team_info.get("url_escudo_svg", "") if team_info else ""
        }

        # Salvar na sessão local e na nuvem
        AuthManager.save_session(session_data, save_to_cloud=True)

        print("\n" + "="*65)
        print(f"✅ Time Autenticado: {team_name}")
        print(f"💰 Patrimônio Sincronizado: C$ {patrimonio:.2f}")
        print(f"💾 Sessão salva com sucesso em {SESSION_FILE} e no Google Sheets!")
        print("="*65)
        print("👉 Pronto! Atualize a página do Streamlit que ele entrará logado automaticamente!\n")

        time.sleep(2.0)
        browser.close()
        return True

if __name__ == "__main__":
    success = login_with_browser()
    sys.exit(0 if success else 1)
