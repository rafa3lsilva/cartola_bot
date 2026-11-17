import pandas as pd
import streamlit as st

from cartola_bot.backtesting import (
    calibrate_weights,
    evaluate_historical_rounds,
    list_complete_snapshots,
    save_calibrated_weights,
)


def render_backtest_tab(config: dict) -> None:
    """Renderiza a aba de Backtesting Histórico (xP vs Real) e Calibração de Pesos."""
    st.subheader("📊 Backtesting & Calibração do Modelo xP")
    st.caption(
        "Avalie a precisão das projeções (xP) contra pontuações reais das rodadas salvas e calibre os pesos do config.yaml."
    )

    rounds_df, players_df = evaluate_historical_rounds()

    if rounds_df.empty:
        st.info(
            "ℹ️ Ainda não há rodadas históricas com arquivo de pontuados correspondente em `data/snapshots/` ou `cache/`."
        )
    else:
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Rodadas Avaliadas", len(rounds_df))
        with k2:
            st.metric("MAE Médio (por atleta)", f"{rounds_df['MAE'].mean():.2f} pts")
        with k3:
            st.metric("RMSE Médio (por atleta)", f"{rounds_df['RMSE'].mean():.2f} pts")
        with k4:
            st.metric("Viés Médio (Real - xP)", f"{rounds_df['Vies_Medio'].mean():+.2f} pts")

        st.markdown("### 📈 Desempenho por Rodada (xP Projetado vs Real)")
        chart_df = rounds_df.set_index("Rodada")[["xP_Time", "Real_Time"]]
        st.bar_chart(chart_df)

        st.dataframe(
            rounds_df.rename(
                columns={
                    "Atletas_Avaliados": "Atletas",
                    "xP_Time": "xP Time",
                    "Real_Time": "Real Time",
                    "Saldo_Time": "Saldo (Real - xP)",
                    "Vies_Medio": "Viés Médio",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        if not players_df.empty:
            st.markdown("### 🎯 Erro Médio por Posição")
            pos_summary = (
                players_df.groupby("Posicao", as_index=False)
                .agg(
                    Atletas=("ID", "count"),
                    xP_Medio=("xP_Projetado", "mean"),
                    Real_Medio=("Pontos_Reais", "mean"),
                    MAE=("Erro_Abs", "mean"),
                    Vies=("Vies", "mean"),
                )
                .round(2)
            )
            st.dataframe(pos_summary, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### ⚙️ Calibração Automática de Pesos (`config.yaml`)")
    snapshots = list_complete_snapshots()
    if not snapshots:
        st.info(
            "📸 Nenhum snapshot completo (`mercado.json` + `partidas.json` + `pontuados.json`) encontrado em `data/snapshots/rodada_<N>/`. "
            "Os snapshots passam a ser salvos automaticamente ao carregar o mercado e acompanhar parciais ao vivo."
        )
        return

    st.success(f"✅ {len(snapshots)} snapshot(s) completo(s) disponível(is): Rodadas {', '.join(map(str, snapshots))}")
    if st.button("🧪 Executar Calibração em Grade", type="primary", key="btn_run_calibration"):
        with st.spinner("Avaliando combinações de pesos nos snapshots..."):
            res = calibrate_weights(config)
        if not res.get("ok"):
            st.warning(res.get("reason", "Não foi possível calibrar."))
        else:
            st.session_state["calibration_result"] = res

    cal_res = st.session_state.get("calibration_result")
    if cal_res and cal_res.get("ok"):
        base = cal_res["baseline"]
        best = cal_res["best_metrics"]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("MAE Baseline", f"{base['mae']:.4f}")
        with c2:
            delta_mae = best["mae"] - base["mae"]
            st.metric("MAE Calibrado", f"{best['mae']:.4f}", delta=f"{delta_mae:+.4f}", delta_color="inverse")
        with c3:
            st.metric("Amostras (Atleta-Rodada)", best["n_samples"])

        weights_df = pd.DataFrame(
            [{"Parâmetro": k, "Valor Recomendado": v} for k, v in cal_res["best_weights"].items()]
        )
        st.dataframe(weights_df, use_container_width=True, hide_index=True)

        if st.button("💾 Aplicar Pesos Calibrados no config.yaml", key="btn_save_calibrated_weights"):
            save_calibrated_weights(cal_res["best_weights"])
            st.success("✅ Pesos atualizados em `cartola_bot/config.yaml`! Recarregue os dados para aplicar.")
