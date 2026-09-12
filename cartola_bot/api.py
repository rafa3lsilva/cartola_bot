import requests
import json
import os
from datetime import datetime, timedelta

class CartolaAPI:
    """Classe para lidar com as requisições à API do Cartola FC."""
    def __init__(self, config):
        self.config = config['api']
        self.headers = {"User-Agent": self.config['user_agent']}
        self.cache_dir = "cache"
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, name):
        """Retorna o caminho do arquivo de cache."""
        return os.path.join(self.cache_dir, f"{name}.json")

    def _is_cache_valid(self, path, max_age_minutes=30):
        """Verifica se o cache ainda é válido (padrão 30 min)."""
        if not os.path.exists(path):
            return False
        file_time = datetime.fromtimestamp(os.path.getmtime(path))
        return datetime.now() - file_time < timedelta(minutes=max_age_minutes)

    def _fetch(self, url, cache_name=None, use_cache=True):
        """Busca dados da URL, usando cache se disponível e realizando fallback gracioso em caso de erro."""
        cache_path = self._get_cache_path(cache_name) if cache_name else None
        
        # 1. Se cache for recente e use_cache for True, carrega direto
        if use_cache and cache_path and self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass

        # 2. Tenta buscar da API oficial
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            data = response.json()

            if cache_path:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)

            return data
        except Exception as e:
            # 3. Fallback: se a API falhar mas existir arquivo de cache, usa o cache existente
            if cache_path and os.path.exists(cache_path):
                print(f"[Aviso API] Falha na requisição ao vivo ({e}). Usando dados em cache local.")
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            raise e

    def get_mercado(self, use_cache=True):
        """Obtém os dados do mercado (atletas, clubes, etc)."""
        url = self.config.get('mercado_url', "https://api.cartola.globo.com/atletas/mercado")
        return self._fetch(url, "mercado", use_cache)

    def get_partidas(self, use_cache=True):
        """Obtém os dados das partidas da rodada."""
        url = self.config.get('partidas_url', "https://api.cartola.globo.com/partidas")
        return self._fetch(url, "partidas", use_cache)

    def get_pontuados(self, rodada=None, *args, **kwargs):
        """Obtém as pontuações e scouts em tempo real dos atletas na rodada (ou de uma rodada histórica)."""
        if rodada is None and 'rodada' in kwargs:
            rodada = kwargs.get('rodada')
        elif rodada is None and len(args) > 0:
            rodada = args[0]
            
        # 1. Primeiro tenta buscar o endpoint ao vivo (/atletas/pontuados)
        live_data = None
        try:
            resp_live = requests.get("https://api.cartola.globo.com/atletas/pontuados", headers=self.headers, timeout=5)
            if resp_live.status_code == 200:
                live_data = resp_live.json()
                with open(self._get_cache_path("pontuados"), 'w', encoding='utf-8') as f:
                    json.dump(live_data, f)
        except Exception:
            pass

        # Se a rodada solicitada coincidir com a rodada ao vivo ou se não especificou rodada
        if live_data and live_data.get('atletas'):
            live_round = str(live_data.get('rodada', ''))
            if rodada is None or str(rodada) == '?' or str(rodada) == live_round:
                return live_data

        # 2. Se for uma rodada histórica específica diferente da rodada ao vivo
        if rodada is not None and str(rodada) != '?':
            url = f"https://api.cartola.globo.com/atletas/pontuados/{rodada}"
            cache_key = f"pontuados_{rodada}"
            try:
                response = requests.get(url, headers=self.headers, timeout=5)
                response.raise_for_status()
                data = response.json()
                if data.get('atletas'):
                    with open(self._get_cache_path(cache_key), 'w', encoding='utf-8') as f:
                        json.dump(data, f)
                    return data
            except Exception:
                pass
                
            # Fallback para cache histórico
            cache_path = self._get_cache_path(cache_key)
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    pass

        # Se tínhamos live_data mesmo sem bater a rodada exata, retorna
        if live_data and live_data.get('atletas'):
            return live_data

        return {"atletas": {}, "rodada": rodada}

    def get_user_team(self, token):
        """Busca os dados do time do usuário logado na Globo (saldo, patrimônio, escalação)."""
        url = "https://api.cartola.globo.com/auth/time"
        headers = dict(self.headers)
        headers["X-GLB-Token"] = token
        headers["Authorization"] = f"Bearer {token}" if not token.startswith("Bearer ") else token
        try:
            response = requests.get(url, headers=headers, cookies={"GLBID": token}, timeout=6)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def save_time_to_globo(self, token, esquema_name, captain_id, starters_ids, reserves_dict=None):
        """
        Envia a escalação completa diretamente para a conta oficial do Cartola FC.
        Esquemas: 3-4-3: 1, 3-5-2: 2, 4-4-2: 3, 4-3-3: 4, 5-3-2: 5
        """
        esquema_map = {
            "3-4-3": 1,
            "3-5-2": 2,
            "4-4-2": 3,
            "4-3-3": 4,
            "5-3-2": 5
        }
        esquema_id = esquema_map.get(esquema_name, 4)
        
        pos_id_map = {
            'Goleiro': 1,
            'Lateral': 2,
            'Zagueiro': 3,
            'Meia': 4,
            'Atacante': 5
        }
        
        reservas_payload = {}
        if reserves_dict:
            for pos_name, r in reserves_dict.items():
                pos_code = str(pos_id_map.get(pos_name, 1))
                r_id = int(r.get('ID', r) if isinstance(r, dict) else r)
                reservas_payload[pos_code] = r_id

        payload = {
            "esquema": esquema_id,
            "capitao": int(captain_id),
            "atletas": [int(i) for i in starters_ids],
            "reservas": reservas_payload
        }
        
        url = "https://api.cartola.globo.com/auth/time/salvar"
        headers = dict(self.headers)
        headers["Content-Type"] = "application/json"
        headers["X-GLB-Token"] = token
        headers["Authorization"] = f"Bearer {token}" if not token.startswith("Bearer ") else token
        
        try:
            response = requests.post(url, json=payload, headers=headers, cookies={"GLBID": token}, timeout=10)
            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                return False, response.text
        except Exception as e:
            return False, str(e)

    def get_mercado_status(self):
        """Obtém o status do mercado (1: Aberto, 2: Fechado/Jogos em andamento, 6: Apuração)."""
        url = "https://api.cartola.globo.com/mercado/status"
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {"status_mercado": 1, "rodada_atual": None}


