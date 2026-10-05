"""Sweep speed and depth to find the most productive stable condition."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import dynamics as dy
from core import roughness as rg, theme


def render(s, res) -> None:
    st.caption("The same model swept over a range of speeds and depths, so you can see "
               "where the productive stable islands are instead of testing one point at "
               "a time.")

    c1, c2, c3 = st.columns(3)
    n_lo = c1.number_input("Speed from (rpm)", 100.0, 200000.0,
                           float(min(max(500.0, s.n_rpm * 0.3), 200000.0)), 100.0)
    n_hi = c2.number_input("Speed to (rpm)", 200.0, 300000.0,
                           float(min(max(s.n_rpm * 2.2, 200.0), 300000.0)), 100.0)
    ap_hi = c3.number_input("Depth to (mm)", 0.05, 200.0,
                            float(min(max(s.ap_mm * 2, 1.0), 200.0)), 0.5)

    n_axis = np.linspace(n_lo, max(n_hi, n_lo + 100), 240)
    ap_axis = np.linspace(0.02, ap_hi, 160)
    limit = np.array([res.limit_at(n) for n in n_axis])
    margin = limit[None, :] / ap_axis[:, None]           # >1 is stable

    mrr = np.outer(ap_axis, np.ones_like(n_axis)) * s.ae_mm * (n_axis * s.teeth * s.fz_mm)
    safe = (margin >= 1.3) & (n_axis[None, :] >= res.n_reliable_min)
    best_mrr = float(np.max(np.where(safe, mrr, 0)))
    bi = np.unravel_index(int(np.argmax(np.where(safe, mrr, 0))), mrr.shape)

    fig = go.Figure()
    fig.add_heatmap(x=n_axis, y=ap_axis, z=np.clip(margin, 0, 3),
                    colorscale=[[0.0, "#f6dcd9"], [0.33, "#f1b9b2"], [0.333, "#dfe9f7"],
                                [0.66, "#9fb4ea"], [1.0, "#2451d6"]],
                    colorbar=dict(title="ap limit / ap"), zmin=0, zmax=3)
    fig.add_contour(x=n_axis, y=ap_axis, z=margin, contours=dict(start=1, end=1, size=0,
                    coloring="none", showlabels=False),
                    line=dict(color=theme.INK, width=2), showscale=False, name="boundary")
    fig.add_scatter(x=[s.n_rpm], y=[s.ap_mm], mode="markers+text", text=["your cut"],
                    textposition="top center", name="your cut",
                    marker=dict(size=13, symbol="x-thin", line=dict(width=3, color=theme.INK),
                                color=theme.INK))
    if best_mrr > 0:
        fig.add_scatter(x=[n_axis[bi[1]]], y=[ap_axis[bi[0]]], mode="markers+text",
                        text=["best MRR"], textposition="bottom center", name="best MRR",
                        marker=dict(size=13, symbol="star", color=theme.DETAIL))
    if res.n_reliable_min > n_axis[0]:
        fig.add_vrect(x0=n_axis[0], x1=min(res.n_reliable_min, n_axis[-1]),
                      fillcolor="rgba(21,35,58,0.12)", line_width=0,
                      annotation_text="lobes not resolved", annotation_position="top left")
    fig.update_layout(height=520, xaxis_title="Spindle speed (rpm)",
                      yaxis_title="Axial depth ap (mm)")
    st.plotly_chart(fig, width="stretch")
    if res.n_reliable_min > n_axis[0]:
        st.caption(f"Below about {res.n_reliable_min:,.0f} rpm the lobes are packed closer "
                   "than the speed grid resolves, so that band is greyed out. Real cuts down "
                   "there are also more stable than this model says, because process damping "
                   "from the flank rubbing against the wavy surface is not included.")

    if best_mrr > 0:
        now = s.ap_mm * s.ae_mm * s.feed_mm_min
        st.success(
            f"Best stable point in this window: {n_axis[bi[1]]:,.0f} rpm at "
            f"{ap_axis[bi[0]]:.2f} mm depth, keeping a 1.3× margin. That is "
            f"{best_mrr:,.0f} mm³/min against {now:,.0f} mm³/min at your current setting "
            f"({best_mrr / max(now, 1e-9):.1f}×).")
    else:
        st.warning("No point in this window keeps a 1.3× margin. Widen the speed range, "
                   "or reduce the radial engagement in the sidebar.")

    st.subheader("Candidate conditions")
    st.caption("Speeds at the peak of each stability pocket, with the finish each would "
               "give at your current feed per tooth.")
    rows = []
    for p in dy.stable_speed_suggestions(res, s.ap_mm, s.n_rpm, n_max=8, margin=1.0):
        r = rg.roughness(s.operation, fz_mm=s.fz_mm, teeth=s.teeth,
                         diameter_mm=s.diameter_mm, nose_radius_mm=s.nose_radius_mm,
                         stepover_mm=s.stepover_mm, runout_mm=s.runout_mm,
                         process_factor=s.process_factor, edge_radius_um=s.edge_radius_um)
        feed = p["speed_rpm"] * s.teeth * s.fz_mm
        rows.append({"speed (rpm)": round(p["speed_rpm"]),
                     "pocket width (rpm)": round(p["width_rpm"]),
                     "ap limit (mm)": round(p["limit_mm"], 2),
                     "max ap at 1.3× margin (mm)": round(p["limit_mm"] / 1.3, 2),
                     "feed (mm/min)": round(feed),
                     "MRR at your ap (mm³/min)": round(s.ap_mm * s.ae_mm * feed),
                     "Ra (µm)": round(r.ra_expected_um, 2)})
    if rows:
        df = pd.DataFrame(rows).sort_values("speed (rpm)")
        st.dataframe(df, hide_index=True, width="stretch")
        st.download_button("Download candidates as CSV", df.to_csv(index=False).encode(),
                           file_name="rajmill_candidates.csv", mime="text/csv")
    else:
        st.info("No stability pocket clears the current depth of cut in the solved speed "
                "range.")
