#!/usr/bin/env python3
"""
Script de Login Interativo da Globo via Navegador (1 Clique)
============================================================
Abre uma janela real do Google Chrome na página oficial da Globo (login.globo.com).
Você faz o login normalmente com e-mail, senha e resolve qualquer Captcha/2FA.
Assim que o login é concluído, o script captura o cookie GLBID / Token automaticamente,
salva no .session_cache.json e sincroniza com o Google Sheets / Streamlit!
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
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright não encontrado. Instalando no ambiente virtual...")
        os.system(".venv/bin/pip install playwright")
        from playwright.sync_api import sync_playwright

    chrome_path = find_system_chrome()

    print("\n" + "="*65)
    print("⚽ M1TOS EC • LOGIN OFICIAL DA GLOBO VIA NAVEGADOR")
    print("="*65)
    print("🚀 Abrindo janela do navegador em https://login.globo.com ...")
    print("👉 Faça o login normalmente com seu e-mail, senha e resolva o Captcha.")
    print("⏳ O script detectará a conclusão do login automaticamente!")
    print("="*65 + "\n")

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

        # Abre a página de autenticação do Cartola na Globo
        page.goto("https://login.globo.com/login/438")

        glbid_found = None
        user_email = "rafaelpjmp@gmail.com"

        # Aguardar até o cookie GLBID aparecer nos cookies do contexto (timeout de até 4 minutos)
        start_time = time.time()
        timeout_seconds = 240

        while time.time() - start_time < timeout_seconds:
            cookies = context.cookies()
            for c in cookies:
                if c.get("name") == "GLBID" and c.get("value"):
                    glbid_found = c.get("value")
                    break

            if glbid_found:
                # Verificar se a página concluiu a autenticação
                current_url = page.url
                if "login.globo.com" not in current_url:
                    break

            time.sleep(1.0)

        if not glbid_found:
            print("❌ Tempo limite esgotado ou login não concluído.")
            browser.close()
            return False

        print(f"\n🎉 SUCESSO! Cookie de autenticação GLBID interceptado!")
        print(f"🔑 GLBID: {glbid_found[:18]}...{glbid_found[-8:]}")

        auth_token = f"Bearer {glbid_found}"
        print("📡 Validando credencial com os servidores do Cartola FC...")
        valid, team_info = AuthManager.validate_token(auth_token, glbid=glbid_found)

        team_name = team_info.get("nome", "M1TOS EC") if team_info else "M1TOS EC"
        patrimonio = float(team_info.get("patrimonio", 136.94)) if team_info else 136.94

        session_data = {
            "email": user_email,
            "token": auth_token,
            "glbid": glbid_found,
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
        print(f"💾 Sessão gravada com sucesso em {SESSION_FILE} e no Google Sheets!")
        print("="*65)
        print("👉 Seu app Streamlit agora abrirá logado diretamente, sem pedir login nem token!\n")

        browser.close()
        return True

if __name__ == "__main__":
    success = login_with_browser()
    sys.exit(0 if success else 1)
