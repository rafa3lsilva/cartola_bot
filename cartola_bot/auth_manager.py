import requests
import json
import os
import time
from datetime import datetime

SESSION_FILE = ".session_cache.json"

class AuthManager:
    """Gerencia autenticação na Globo, ciclo de vida de tokens e persistência de sessão."""
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    @staticmethod
    def login_with_credentials(email, password):
        """
        Realiza login direto na API de autenticação da Globo (login.globo.com).
        Retorna (sucesso: bool, dados_sessao_ou_erro: dict/str)
        """
        if not email or not password:
            return False, "E-mail e senha são obrigatórios."

        url = "https://login.globo.com/api/authentication"
        payload = {
            "payload": {
                "email": email.strip(),
                "password": password.strip(),
                "serviceId": 438
            }
        }
        
        try:
            resp = requests.post(url, json=payload, headers=AuthManager.HEADERS, timeout=12)
            
            if resp.status_code == 200:
                data = resp.json()
                user_info = data.get("user", {})
                glbid = user_info.get("glbId", "")
                token = user_info.get("token", "") or glbid
                
                cookies = resp.cookies.get_dict()
                if "GLBID" in cookies:
                    glbid = cookies["GLBID"]
                
                auth_token = f"Bearer {token}" if not token.startswith("Bearer ") else token
                
                valid, team_info = AuthManager.validate_token(auth_token, glbid=glbid)
                
                session_data = {
                    "email": email.strip(),
                    "token": auth_token,
                    "glbid": glbid,
                    "authenticated_at": datetime.now().isoformat(),
                    "team_name": team_info.get("nome", "M1TOS EC") if team_info else "M1TOS EC",
                    "nome_cartola": team_info.get("nome_cartola", "") if team_info else "",
                    "patrimonio": float(team_info.get("patrimonio", 141.66)) if team_info else 141.66,
                    "foto_perfil": team_info.get("foto_perfil", "") if team_info else "",
                    "url_escudo_svg": team_info.get("url_escudo_svg", "") if team_info else ""
                }
                return True, session_data

            elif resp.status_code == 401 or "InvalidUserOrPassword" in resp.text:
                return False, "E-mail ou senha incorretos na conta Globo."
            elif "captcha" in resp.text.lower():
                return False, "A Globo solicitou verificação de segurança (Captcha). Você pode colar seu token diretamente."
            else:
                return False, f"Resposta da Globo ({resp.status_code}): {resp.text[:150]}"
                
        except requests.exceptions.Timeout:
            return False, "Tempo de resposta esgotado ao conectar à Globo. Tente novamente."
        except Exception as e:
            return False, f"Erro inesperado no login: {str(e)}"

    @staticmethod
    def validate_token(token, glbid=None):
        """
        Verifica se um Bearer token ou GLBID é válido consultando os dados do time do usuário.
        Retorna (valido: bool, time_info: dict)
        """
        if not token:
            return False, None
            
        url = "https://api.cartola.globo.com/auth/time/info"
        headers = dict(AuthManager.HEADERS)
        headers["Authorization"] = f"Bearer {token}" if not token.startswith("Bearer ") else token
        headers["X-GLB-Token"] = token.replace("Bearer ", "")
        
        cookies = {}
        if glbid:
            cookies["GLBID"] = glbid
        else:
            cookies["GLBID"] = token.replace("Bearer ", "")
            
        try:
            resp = requests.get(url, headers=headers, cookies=cookies, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                time_data = data.get("time", {})
                return True, time_data
            else:
                return False, None
        except Exception:
            return False, None

    @staticmethod
    def load_active_session():
        """
        Carrega a sessão ativa prioritariamente de:
        1. Google Sheets (nuvem)
        2. Arquivo local .session_cache.json
        """
        from cartola_bot.gsheets_manager import load_auth_session
        session_data = load_auth_session()
        if session_data and session_data.get("token"):
            return session_data

        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("token"):
                        return data
            except Exception:
                pass

        return None

    @staticmethod
    def save_session(session_dict, save_to_cloud=True):
        """Salva a sessão localmente e no Google Sheets."""
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(session_dict, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
            
        if save_to_cloud:
            try:
                from cartola_bot.gsheets_manager import save_auth_session
                save_auth_session(session_dict)
            except Exception:
                pass

    @staticmethod
    def logout():
        """Limpa a sessão local e da nuvem."""
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
            except Exception:
                pass
        try:
            from cartola_bot.gsheets_manager import clear_auth_session
            clear_auth_session()
        except Exception:
            pass
