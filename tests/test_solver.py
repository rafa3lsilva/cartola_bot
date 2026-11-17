import pandas as pd

from cartola_bot.solver import TeamOptimizer
from cartola_bot.utils.config_loader import load_config


def _build_synthetic_pool() -> pd.DataFrame:
    """Cria um pool de atletas sintético com folga para 4-3-3 respeitando limites de clube."""
    clubs = ["FLA", "PAL", "BOT", "CAM", "INT", "SAO", "GRE", "BAH"]
    specs = [
        ("Goleiro", 3, 8.0, 5.0),
        ("Lateral", 4, 9.0, 6.0),
        ("Zagueiro", 4, 9.0, 5.5),
        ("Meia", 6, 10.0, 7.0),
        ("Atacante", 6, 11.0, 8.5),
        ("Técnico", 3, 7.0, 4.5),
    ]
    rows = []
    idx = 1
    for pos, count, base_price, base_xp in specs:
        for j in range(count):
            club = clubs[(idx + j) % len(clubs)]
            rows.append(
                {
                    "ID": idx,
                    "Nome": f"{pos[:3]}_{idx}",
                    "Posicao": pos,
                    "Clube": club,
                    "Preco": base_price + j * 0.5,
                    "Media": base_xp,
                    "Media_Ajustada": base_xp + j * 0.4,
                    "Upside": base_xp + j * 0.8 + 2.0,
                    "Goals_Per_Game": 0.4 if pos == "Atacante" else 0.1,
                    "Confronto": f"{club} x ADV{j}",
                    "Opp_Abrev": f"ADV{j}",
                }
            )
            idx += 1
    return pd.DataFrame(rows)


def test_optimizer_solves_433_within_budget_and_captain():
    config = load_config("cartola_bot/config.yaml")
    optimizer = TeamOptimizer(config)
    df = _build_synthetic_pool()

    budget = 130.0
    selected_df = optimizer.optimize(
        df, budget=budget, formation_name="4-3-3", max_players_per_club=5
    )

    assert selected_df is not None
    assert len(selected_df) == 12
    assert float(selected_df["Preco"].sum()) <= budget + 1e-6
    assert float(selected_df["Media_Ajustada"].sum()) > 0
    assert selected_df["Is_Capitao"].sum() == 1
    # Técnico não pode ser capitão
    cap_row = selected_df[selected_df["Is_Capitao"]].iloc[0]
    assert cap_row["Posicao"] != "Técnico"
    # Contagem exata da formação 4-3-3
    pos_counts = selected_df["Posicao"].value_counts().to_dict()
    assert pos_counts == {
        "Goleiro": 1,
        "Lateral": 2,
        "Zagueiro": 2,
        "Meia": 3,
        "Atacante": 3,
        "Técnico": 1,
    }


def test_optimizer_best_formation_returns_summary():
    config = load_config("cartola_bot/config.yaml")
    optimizer = TeamOptimizer(config)
    df = _build_synthetic_pool()

    best_form, best_df, best_score, summary = optimizer.optimize_best_formation(
        df, budget=130.0, max_players_per_club=5
    )

    assert best_form in config["formations"]
    assert len(best_df) == 12
    assert float(best_df["Preco"].sum()) <= 130.0 + 1e-6
    assert best_score > 0
    assert len(summary) >= 1
