from cartola_bot.notifier import check_lineup_risks, minutes_until_close


def test_minutes_until_close_open_and_closed():
    assert minutes_until_close({"status_mercado": 2, "fechamento": {"timestamp": 2000}}, now_ts=1000) is None
    assert minutes_until_close({"status_mercado": 1, "fechamento": {"timestamp": 4600}}, now_ts=1000) == 60.0


def test_check_lineup_risks_detects_non_provavel_starter_and_reserve():
    official_team = {
        "rodada": 33,
        "starters": [
            {"ID": 10, "Nome": "Pedro", "Posicao": "Atacante", "Clube": "FLA"},
            {"ID": 20, "Nome": "Rossi", "Posicao": "Goleiro", "Clube": "FLA"},
        ],
        "reserves": {
            "Atacante": {"ID": 30, "Nome": "Bruno", "Clube": "PAL"},
        },
    }
    mercado_data = {
        "clubes": {"262": {"abreviacao": "FLA"}, "275": {"abreviacao": "PAL"}},
        "atletas": [
            {"atleta_id": 10, "apelido": "Pedro", "clube_id": 262, "status_id": 5},
            {"atleta_id": 20, "apelido": "Rossi", "clube_id": 262, "status_id": 7},
            {"atleta_id": 30, "apelido": "Bruno", "clube_id": 275, "status_id": 3},
        ],
    }

    risks = check_lineup_risks(official_team, mercado_data)
    assert len(risks) == 2
    assert risks[0]["role"] == "Titular"
    assert risks[0]["status_nome"] == "Contundido"
    assert risks[1]["role"] == "Reserva"
    assert risks[1]["status_nome"] == "Suspenso"
