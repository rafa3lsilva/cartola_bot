from cartola_bot.scoring import Scorer
from cartola_bot.utils.config_loader import load_config


def test_scorer_process_data_computes_xp_and_sg():
    config = load_config("cartola_bot/config.yaml")
    scorer = Scorer(config)

    mercado_data = {
        "posicoes": {
            "1": {"nome": "Goleiro"},
            "5": {"nome": "Atacante"},
        },
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
                "variacao_num": 1.2,
                "minimo_para_valorizar": 6.5,
                "scout": {"G": 8, "A": 2, "FD": 12},
                "foto": "",
            },
            {
                "atleta_id": 20,
                "apelido": "Rossi",
                "clube_id": 262,
                "posicao_id": 1,
                "status_id": 7,
                "preco_num": 9.0,
                "media_num": 4.5,
                "jogos_num": 10,
                "pontos_num": 5.0,
                "variacao_num": 0.3,
                "minimo_para_valorizar": 3.0,
                "scout": {"SG": 5, "DE": 20},
                "foto": "",
            },
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
                "aproveitamento_mandante": ["v", "v", "v", "e", "v"],
                "aproveitamento_visitante": ["d", "d", "e", "d", "d"],
                "valida": True,
            }
        ],
    }

    df = scorer.process_data(mercado_data, partidas_data)
    assert not df.empty
    assert set(df["ID"].tolist()) == {10, 20}
    assert "Media_Ajustada" in df.columns
    assert "Upside" in df.columns
    assert (df["Media_Ajustada"] > 0).all()
    pedro = df[df["ID"] == 10].iloc[0]
    assert pedro["Posicao"] == "Atacante"
    assert pedro["Clube"] == "FLA"
