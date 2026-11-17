"""Pipeline de backtesting, snapshots por rodada e calibração de pesos do modelo xP."""

from __future__ import annotations

import copy
import glob
import json
import math
import os
from itertools import product

import numpy as np
import pandas as pd
import yaml

from cartola_bot.scoring import Scorer


def save_round_snapshot(
    rodada: int | str,
    mercado_data: dict | None = None,
    partidas_data: dict | None = None,
    pontuados_data: dict | None = None,
    base_dir: str = "data/snapshots",
) -> str | None:
    """Salva snapshot de mercado, partidas e/ou pontuados para backtesting futuro."""
    if not rodada or str(rodada) == "?":
        return None
    try:
        rodada_int = int(rodada)
    except (ValueError, TypeError):
        return None

    round_dir = os.path.join(base_dir, f"rodada_{rodada_int}")
    os.makedirs(round_dir, exist_ok=True)

    payloads = {
        "mercado.json": mercado_data,
        "partidas.json": partidas_data,
        "pontuados.json": pontuados_data,
    }
    for filename, data in payloads.items():
        if data:
            path = os.path.join(round_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

    return round_dir


def _load_pontuados_for_round(
    rodada_int: int,
    snapshots_dir: str = "data/snapshots",
    cache_dir: str = "cache",
) -> dict:
    """Busca o dicionário de pontuados para uma rodada nos snapshots ou no cache."""
    candidates = [
        os.path.join(snapshots_dir, f"rodada_{rodada_int}", "pontuados.json"),
        os.path.join(cache_dir, f"pontuados_{rodada_int}.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                atletas = data.get("atletas", {})
                if atletas:
                    return atletas
            except Exception:
                pass
    return {}


def evaluate_historical_rounds(
    historico_dir: str = "data/historico",
    snapshots_dir: str = "data/snapshots",
    cache_dir: str = "cache",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compara escalações salvas em data/historico/rodada_*.json com pontuações reais.

    Retorna:
        (rounds_df, players_df)
    """
    if not os.path.exists(historico_dir):
        return pd.DataFrame(), pd.DataFrame()

    round_rows: list[dict] = []
    player_rows: list[dict] = []

    files = sorted(glob.glob(os.path.join(historico_dir, "rodada_*.json")))
    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                team_data = json.load(f)
        except Exception:
            continue

        rodada_num = team_data.get("rodada")
        if rodada_num is None:
            continue
        try:
            rodada_int = int(rodada_num)
        except (ValueError, TypeError):
            continue

        pontuados = _load_pontuados_for_round(rodada_int, snapshots_dir=snapshots_dir, cache_dir=cache_dir)
        if not pontuados:
            continue

        starters = team_data.get("starters", [])
        captain_id = team_data.get("captain_id")
        if not starters:
            continue

        errors = []
        sq_errors = []
        diffs = []
        proj_total = 0.0
        real_total = 0.0
        evaluated_count = 0

        for s in starters:
            a_id = s.get("ID") or s.get("atleta_id")
            if a_id is None:
                continue
            is_cap = captain_id is not None and int(a_id) == int(captain_id)
            mult = 1.5 if is_cap else 1.0

            xp_base = float(s.get("Media_Ajustada", 0.0) or 0.0)
            xp_proj = xp_base * mult
            proj_total += xp_proj

            pinfo = pontuados.get(str(a_id))
            if pinfo is None:
                continue

            real_base = float(pinfo.get("pontuacao", 0.0) or 0.0)
            real_pts = real_base * mult
            real_total += real_pts
            evaluated_count += 1

            diff = real_pts - xp_proj
            errors.append(abs(diff))
            sq_errors.append(diff**2)
            diffs.append(diff)

            player_rows.append(
                {
                    "Rodada": rodada_int,
                    "ID": int(a_id),
                    "Nome": s.get("Nome", ""),
                    "Posicao": s.get("Posicao", ""),
                    "Clube": s.get("Clube", ""),
                    "Capitao": is_cap,
                    "xP_Projetado": round(xp_proj, 2),
                    "Pontos_Reais": round(real_pts, 2),
                    "Erro_Abs": round(abs(diff), 2),
                    "Vies": round(diff, 2),
                }
            )

        if evaluated_count > 0:
            mae = float(np.mean(errors))
            rmse = float(math.sqrt(np.mean(sq_errors)))
            bias = float(np.mean(diffs))
            round_rows.append(
                {
                    "Rodada": rodada_int,
                    "Atletas_Avaliados": evaluated_count,
                    "xP_Time": round(proj_total, 2),
                    "Real_Time": round(real_total, 2),
                    "Saldo_Time": round(real_total - proj_total, 2),
                    "MAE": round(mae, 2),
                    "RMSE": round(rmse, 2),
                    "Vies_Medio": round(bias, 2),
                }
            )

    rounds_df = pd.DataFrame(round_rows)
    players_df = pd.DataFrame(player_rows)
    if not rounds_df.empty:
        rounds_df = rounds_df.sort_values("Rodada").reset_index(drop=True)
    return rounds_df, players_df


def list_complete_snapshots(snapshots_dir: str = "data/snapshots") -> list[int]:
    """Lista rodadas em data/snapshots que possuem mercado, partidas e pontuados."""
    if not os.path.exists(snapshots_dir):
        return []
    rounds: list[int] = []
    for entry in os.listdir(snapshots_dir):
        if not entry.startswith("rodada_"):
            continue
        r_dir = os.path.join(snapshots_dir, entry)
        required = [os.path.join(r_dir, f) for f in ("mercado.json", "partidas.json", "pontuados.json")]
        if all(os.path.exists(p) for p in required):
            try:
                rounds.append(int(entry.replace("rodada_", "")))
            except ValueError:
                pass
    return sorted(rounds)


def evaluate_snapshots_with_weights(
    weights_override: dict | None,
    config: dict,
    snapshots_dir: str = "data/snapshots",
) -> dict:
    """Roda o Scorer com pesos candidatos nos snapshots completos e mede MAE/RMSE/Viés."""
    rounds = list_complete_snapshots(snapshots_dir)
    if not rounds:
        return {"n_rounds": 0, "n_samples": 0, "mae": None, "rmse": None, "bias": None}

    cfg = copy.deepcopy(config)
    if weights_override:
        cfg.setdefault("scoring", {}).setdefault("weights", {}).update(weights_override)

    scorer = Scorer(cfg)
    abs_errors: list[float] = []
    sq_errors: list[float] = []
    diffs: list[float] = []

    for r in rounds:
        r_dir = os.path.join(snapshots_dir, f"rodada_{r}")
        with open(os.path.join(r_dir, "mercado.json"), "r", encoding="utf-8") as f:
            mercado = json.load(f)
        with open(os.path.join(r_dir, "partidas.json"), "r", encoding="utf-8") as f:
            partidas = json.load(f)
        with open(os.path.join(r_dir, "pontuados.json"), "r", encoding="utf-8") as f:
            pontuados_raw = json.load(f)

        pontuados = pontuados_raw.get("atletas", {})
        if not pontuados:
            continue

        df = scorer.process_data(mercado, partidas)
        for _, row in df.iterrows():
            a_id = str(int(row["ID"]))
            if a_id not in pontuados:
                continue
            real_pts = float(pontuados[a_id].get("pontuacao", 0.0) or 0.0)
            xp_proj = float(row["Media_Ajustada"])
            diff = real_pts - xp_proj
            abs_errors.append(abs(diff))
            sq_errors.append(diff**2)
            diffs.append(diff)

    if not abs_errors:
        return {"n_rounds": len(rounds), "n_samples": 0, "mae": None, "rmse": None, "bias": None}

    return {
        "n_rounds": len(rounds),
        "n_samples": len(abs_errors),
        "mae": round(float(np.mean(abs_errors)), 4),
        "rmse": round(float(math.sqrt(np.mean(sq_errors))), 4),
        "bias": round(float(np.mean(diffs)), 4),
    }


def calibrate_weights(
    config: dict,
    snapshots_dir: str = "data/snapshots",
    param_grid: dict[str, list[float]] | None = None,
) -> dict:
    """
    Busca em grade pelos melhores pesos de scoring para minimizar o MAE nos snapshots.
    """
    baseline = evaluate_snapshots_with_weights(None, config, snapshots_dir=snapshots_dir)
    if not baseline["n_samples"]:
        return {"ok": False, "reason": "Nenhum snapshot completo disponível para calibração.", "baseline": baseline}

    if param_grid is None:
        param_grid = {
            "home_attack_multiplier": [1.08, 1.15, 1.22],
            "away_attack_multiplier": [0.80, 0.85, 0.92],
            "opp_strength_weight": [0.010, 0.015, 0.020],
            "sg_base_prob": [0.25, 0.30, 0.35],
        }

    keys = list(param_grid.keys())
    best_weights = dict(config.get("scoring", {}).get("weights", {}))
    best_metrics = baseline

    for combo in product(*(param_grid[k] for k in keys)):
        candidate = dict(zip(keys, combo))
        metrics = evaluate_snapshots_with_weights(candidate, config, snapshots_dir=snapshots_dir)
        if metrics["mae"] is not None and metrics["mae"] < best_metrics["mae"]:
            best_metrics = metrics
            best_weights.update(candidate)

    return {
        "ok": True,
        "baseline": baseline,
        "best_metrics": best_metrics,
        "best_weights": best_weights,
    }


def save_calibrated_weights(weights: dict, config_path: str = "cartola_bot/config.yaml") -> None:
    """Atualiza os pesos calibrados no arquivo config.yaml preservando as demais seções."""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    cfg.setdefault("scoring", {}).setdefault("weights", {}).update(weights)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
