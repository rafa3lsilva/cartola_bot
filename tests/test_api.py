import json
from unittest.mock import MagicMock, patch

from cartola_bot.api import CartolaAPI
from cartola_bot.utils.config_loader import load_config


def test_api_get_mercado_fetches_and_caches(tmp_path):
    config = load_config("cartola_bot/config.yaml")
    api = CartolaAPI(config)
    api.cache_dir = str(tmp_path)

    fake_payload = {"atletas": [{"atleta_id": 1, "apelido": "Teste"}]}
    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_payload
    mock_resp.raise_for_status.return_value = None

    with patch("cartola_bot.api.requests.get", return_value=mock_resp) as mock_get:
        data = api.get_mercado(use_cache=False)
        assert data == fake_payload
        mock_get.assert_called_once()

    # Segunda chamada com use_cache=True deve ler do arquivo sem chamar requests.get
    with patch("cartola_bot.api.requests.get") as mock_get_cached:
        cached = api.get_mercado(use_cache=True)
        assert cached == fake_payload
        mock_get_cached.assert_not_called()


def test_api_fallback_to_stale_cache_on_network_error(tmp_path):
    config = load_config("cartola_bot/config.yaml")
    api = CartolaAPI(config)
    api.cache_dir = str(tmp_path)

    cache_file = tmp_path / "partidas.json"
    stale_data = {"rodada": 32, "partidas": []}
    cache_file.write_text(json.dumps(stale_data), encoding="utf-8")

    with patch("cartola_bot.api.requests.get", side_effect=RuntimeError("offline")):
        data = api.get_partidas(use_cache=False)
        assert data == stale_data
