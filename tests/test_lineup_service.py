import pandas as pd

from cartola_bot.lineup_service import (
    order_defensive_line,
    parse_globo_team_payload,
    validate_lineup_rules,
)


def _make_starter_df():
    rows = [
        {"ID": 1, "Nome": "Gol", "Posicao": "Goleiro", "Preco": 10.0},
        {"ID": 2, "Nome": "Lat1", "Posicao": "Lateral", "Preco": 8.0},
        {"ID": 3, "Nome": "Lat2", "Posicao": "Lateral", "Preco": 12.0},
        {"ID": 4, "Nome": "Zag1", "Posicao": "Zagueiro", "Preco": 9.0},
        {"ID": 5, "Nome": "Zag2", "Posicao": "Zagueiro", "Preco": 11.0},
        {"ID": 6, "Nome": "Mei1", "Posicao": "Meia", "Preco": 10.0},
        {"ID": 7, "Nome": "Mei2", "Posicao": "Meia", "Preco": 14.0},
        {"ID": 8, "Nome": "Mei3", "Posicao": "Meia", "Preco": 15.0},
        {"ID": 9, "Nome": "Ata1", "Posicao": "Atacante", "Preco": 11.0},
        {"ID": 10, "Nome": "Ata2", "Posicao": "Atacante", "Preco": 16.0},
        {"ID": 11, "Nome": "Ata3", "Posicao": "Atacante", "Preco": 18.0},
        {"ID": 12, "Nome": "Tec", "Posicao": "Técnico", "Preco": 9.0},
    ]
    return pd.DataFrame(rows)


def test_order_defensive_line_four_defenders():
    df = pd.DataFrame(
        [
            {"ID": 4, "Posicao": "Zagueiro"},
            {"ID": 2, "Posicao": "Lateral"},
            {"ID": 5, "Posicao": "Zagueiro"},
            {"ID": 3, "Posicao": "Lateral"},
        ]
    )
    ordered = order_defensive_line(df)
    assert ordered["Posicao"].tolist() == ["Lateral", "Zagueiro", "Zagueiro", "Lateral"]
    assert ordered["ID"].tolist() == [2, 4, 5, 3]


def test_order_defensive_line_three_zagueiros():
    df = pd.DataFrame(
        [
            {"ID": 4, "Posicao": "Zagueiro"},
            {"ID": 5, "Posicao": "Zagueiro"},
            {"ID": 6, "Posicao": "Zagueiro"},
        ]
    )
    ordered = order_defensive_line(df)
    assert ordered["ID"].tolist() == [4, 5, 6]


def test_validate_lineup_rules_valid():
    starters = _make_starter_df()
    reservas = {
        "Goleiro": {"Nome": "ResGol", "Preco": 10.0, "Status_ID": 7},
        "Atacante": {"Nome": "ResAta", "Preco": 9.5, "Status_ID": 7},
    }
    ok, errors = validate_lineup_rules(starters, reservas)
    assert ok is True
    assert errors == []


def test_validate_lineup_rules_rejects_expensive_and_non_provavel_reserve():
    starters = _make_starter_df()
    reservas = {
        "Lateral": {"Nome": "ResLatCaro", "Preco": 9.0, "Status_ID": 7},
        "Meia": {"Nome": "ResMeiDuvida", "Preco": 5.0, "Status_ID": 2, "Status_Nome": "Dúvida"},
    }
    ok, errors = validate_lineup_rules(starters, reservas)
    assert ok is False
    assert len(errors) == 2


def test_validate_lineup_rules_rejects_incomplete_team():
    starters = _make_starter_df().iloc[:10]
    ok, errors = validate_lineup_rules(starters, {})
    assert ok is False
    assert any("10 de 12" in e for e in errors)


def test_parse_globo_team_payload_dict_and_list():
    payload_dict = {
        "atletas": [{"atleta_id": 101}, 102],
        "capitao_id": 101,
        "reserva_luxo_id": 205,
        "reservas": {"1": 201, "atacante": {"atleta_id": 205}},
    }
    parsed = parse_globo_team_payload(payload_dict)
    assert parsed["starters_ids"] == [101, 102]
    assert parsed["cap_id"] == 101
    assert parsed["super_sub_id"] == 205
    assert parsed["reserves_ids"] == {"Goleiro": 201, "Atacante": 205}

    payload_list = {
        "atletas": [1, 2],
        "capitao": 2,
        "reservas": [{"posicao_id": 3, "atleta_id": 301}],
    }
    parsed_list = parse_globo_team_payload(payload_list)
    assert parsed_list["reserves_ids"] == {"Zagueiro": 301}
