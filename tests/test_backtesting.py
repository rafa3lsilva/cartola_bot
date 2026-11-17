import json

import yaml

from cartola_bot.backtesting import (
    calibrate_weights,
    evaluate_historical_rounds,
    list_complete_snapshots,
    save_calibrated_weights,
    save_round_snapshot,
)
from cartola_bot.utils.config_loader import load_config


def test_save_round_snapshot_and_list(tmp_path):
    snap_dir = save_round_snapshot(
        rodada=30,
        mercado_data={"atletas": []},
        partidas_data={"rodada": 30, "partidas": []},
        pontuados_data={"atletas": {"1": {"pontuacao": 5.0}}},
        base_dir=str(tmp_path),
    )
    assert snap_dir is not None
    assert list_complete_snapshots(str(tmp_path)) == [30]
    assert save_round_snapshot("?", mercado_data={"a": 1}, base_dir=str(tmp_path)) is None


def test_evaluate_historical_rounds_with_captain_multiplier(tmp_path):
    hist_dir = tmp_path / "historico"
    cache_dir = tmp_path / "cache"
    hist_dir.mkdir()
    cache_dir.mkdir()

    team_payload = {
        "rodada": 25,
        "captain_id": 10,
        "starters": [
            {"ID": 10, "Nome": "Cap", "Posicao": "Atacante", "Clube": "FLA", "Media_Ajustada": 8.0},
            {"ID": 20, "Nome": "Gol", "Posicao": "Goleiro", "Clube": "PAL", "Media_Ajustada": 4.0},
        ],
    }
    (hist_dir / "rodada_25.json").write_text(json.dumps(team_payload), encoding="utf-8")

    # Cap fez 10.0 bruto -> 15.0 (1.5x) vs 12.0 projetado (diff = +3.0)
    # Gol fez 3.0 bruto -> 3.0 vs 4.0 projetado (diff = -1.0)
    pontuados_payload = {
        "atletas": {
            "10": {"pontuacao": 10.0},
            "20": {"pontuacao": 3.0},
        }
    }
    (cache_dir / "pontuados_25.json").write_text(json.dumps(pontuados_payload), encoding="utf-8")

    rounds_df, players_df = evaluate_historical_rounds(
        historico_dir=str(hist_dir),
        snapshots_dir=str(tmp_path / "snapshots"),
        cache_dir=str(cache_dir),
    )

    assert len(rounds_df) == 1
    row = rounds_df.iloc[0]
    assert row["Rodada"] == 25
    assert row["xP_Time"] == 16.0
    assert row["Real_Time"] == 18.0
    assert row["MAE"] == 2.0
    assert row["Vies_Medio"] == 1.0
    assert len(players_df) == 2


def test_calibrate_weights_and_save(tmp_path):
    config = load_config("cartola_bot/config.yaml")
    snap_dir = tmp_path / "snapshots"
    mercado_data = {
        "posicoes": {"5": {"nome": "Atacante"}},
        "clubes": {
            "262": {"id": 262, "abreviacao": "FLA", "nome": "Flamengo", "posicao": 1},
            "263": {"id": 263, "abreviacao": "BOT", "nome": "Botafogo", "posicao": 18},
        },
        "atletas": [
            {
                "atleta_id": 10,
                "apelido": "Pedro",
                "clube_id": 262,
                "posicao_id": 5,
                "status_id": 7,
                "preco_num": 15.0,
                "media_num": 8.0,
                "jogos_num": 10,
                "pontos_num": 12.0,
                "variacao_num": 1.0,
                "scout": {"G": 6, "FD": 10},
                "foto": "",
            }
        ],
    }
    partidas_data = {
        "rodada": 33,
        "partidas": [
            {
                "clube_casa_id": 262,
                "clube_visitante_id": 263,
                "clube_casa_posicao": 1,
                "clube_visitante_posicao": 18,
                "aproveitamento_mandante": ["v", "v", "v", "v", "v"],
                "aproveitamento_visitante": ["d", "d", "d", "d", "d"],
                "valida": True,
            }
        ],
    }
    pontuados_data = {"atletas": {"10": {"pontuacao": 9.5}}}

    save_round_snapshot(
        rodada=33,
        mercado_data=mercado_data,
        partidas_data=partidas_data,
        pontuados_data=pontuados_data,
        base_dir=str(snap_dir),
    )

    res = calibrate_weights(
        config,
        snapshots_dir=str(snap_dir),
        param_grid={"home_attack_multiplier": [1.05, 1.15]},
    )
    assert res["ok"] is True
    assert res["best_metrics"]["n_samples"] == 1

    cfg_copy = tmp_path / "config.yaml"
    cfg_copy.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    save_calibrated_weights({"home_attack_multiplier": 1.05}, config_path=str(cfg_copy))
    reloaded = yaml.safe_load(cfg_copy.read_text(encoding="utf-8"))
    assert reloaded["scoring"]["weights"]["home_attack_multiplier"] == 1.05
