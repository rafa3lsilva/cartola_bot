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
            
        if rodada is not None and str(rodada) != '?':
            url = f"https://api.cartola.globo.com/atletas/pontuados/{rodada}"
            cache_key = f"pontuados_{rodada}"
        else:
            url = "https://api.cartola.globo.com/atletas/pontuados"
            cache_key = "pontuados"
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            with open(self._get_cache_path(cache_key), 'w', encoding='utf-8') as f:
                json.dump(data, f)
            return data
        except Exception as e:
            cache_path = self._get_cache_path(cache_key)
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"atletas": {}, "rodada": rodada}

    def get_mercado_status(self):
        """Obtém o status do mercado (1: Aberto, 2: Fechado/Jogos em andamento, 6: Apuração)."""
        url = "https://api.cartola.globo.com/mercado/status"
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {"status_mercado": 1, "rodada_atual": None}
