"""Predict the outcome of one cutting condition."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import dynamics as dy
from core import recommend as rc, roughness as rg, theme


def render(s, res) -> None:
    """One tab: verdict, lobe diagram, roughness breakdown and what to change."""
    phi = s.angles
    rough = rg.roughness(s.operation, fz_mm=s.fz_mm, teeth=s.teeth,
                         diameter_mm=s.diameter_mm, nose_radius_mm=s.nose_radius_mm,
                         stepover_mm=s.stepover_mm, runout_mm=s.runout_mm,
                         process_factor=s.process_factor, edge_radius_um=s.edge_radius_um,
                         unstable=s.ap_mm > res.limit_at(s.n_rpm))

    a = rc.assess(res=res, ap_mm=s.ap_mm, ae_mm=s.ae_mm, n_rpm=s.n_rpm, teeth=s.teeth,
                  fz_mm=s.fz_mm, feed_mm_min=s.feed_mm_min, rough=rough,
                  target_ra_um=s.target_ra_um, operation=s.operation,
                  diameter_mm=s.diameter_mm, nose_radius_mm=s.nose_radius_mm,
                  process_factor=s.process_factor, dyn=s.dyn, Kt=s.Kt, Kr=s.Kr,
                  direction=s.direction)

    # ---------------------------------------------------------------- verdict
    colour = theme.GOOD if (a.stable and a.meets_target is not False) else theme.BAD
    st.markdown(f"<p class='rm-verdict' style='color:{colour}'>{a.headline}</p>",
                unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Process state", "Chatter" if not a.stable else "Stable",
              f"{a.margin:.2f}× the limit" if a.stable else f"{1 / a.margin:.2f}× over",
              delta_color="normal" if a.stable else "inverse")
    m2.metric("Limiting depth here", f"{a.ap_limit_mm:.2f} mm", f"using {s.ap_mm:.2f} mm")
    m3.metric("Expected Ra", f"{rough.ra_expected_um:.2f} µm", rough.grade)
    mrr_txt = (f"{a.mrr_mm3_min / 1000:,.1f}k" if a.mrr_mm3_min >= 10_000
               else f"{a.mrr_mm3_min:,.0f}")
    m4.metric("Removal rate (mm³/min)", mrr_txt, f"{s.feed_mm_min:,.0f} mm/min feed")

    st.write(a.state_reason)
    st.write(a.finish_reason)
    theme.caption_row([
        ("Cutting speed", f"{s.cutting_speed_m_min:,.0f} m/min"),
        ("Tooth passing", f"{a.tooth_passing_hz:,.0f} Hz"),
        ("Chatter frequency", f"{a.chatter_hz:,.0f} Hz" if a.chatter_hz else "—"),
        ("Immersion", f"{s.ae_mm / s.diameter_mm * 100:.0f}% ({s.direction})"),
        ("Engagement", f"{np.degrees(phi[0]):.0f}° to {np.degrees(phi[1]):.0f}°"),
    ])
    st.write("")

    tab_sld, tab_ra, tab_act, tab_num = st.tabs(
        ["Stability diagram", "Roughness", "What to change", "Numbers"])

    # ---------------------------------------------------------------- lobes
    with tab_sld:
        fig = go.Figure()
        top = max(s.ap_mm * 2.5, float(np.median(res.alim_grid)) * 3.0)
        fig.add_scatter(x=res.n_grid, y=np.minimum(res.alim_grid, top * 1.5),
                        name="Stability limit", line=dict(color=theme.SIGNAL, width=2),
                        fill="tozeroy", fillcolor="rgba(36,81,214,0.08)")
        fig.add_scatter(x=[s.n_rpm], y=[s.ap_mm], mode="markers+text",
                        name="Your cut", text=["your cut"], textposition="top center",
                        marker=dict(size=14, symbol="x-thin",
                                    line=dict(width=3, color=theme.BAD if not a.stable
                                              else theme.GOOD),
                                    color=theme.BAD if not a.stable else theme.GOOD))
        # Suggested pockets are only useful when the current point fails; drawing
        # them on a stable cut just crowds the operating-point marker.
        for p in ([] if a.stable
                  else dy.stable_speed_suggestions(res, s.ap_mm, s.n_rpm, n_max=3)):
            fig.add_scatter(x=[p["speed_rpm"]], y=[s.ap_mm], mode="markers",
                            name=f"{p['speed_rpm']:,.0f} rpm pocket",
                            marker=dict(size=11, symbol="circle-open",
                                        line=dict(width=2.5), color=theme.DETAIL))
        if res.n_reliable_min > res.n_grid[0]:
            fig.add_vrect(x0=res.n_grid[0], x1=res.n_reliable_min,
                          fillcolor="rgba(21,35,58,0.12)", line_width=0,
                          annotation_text="lobes not resolved", annotation_position="top left")
        fig.update_layout(height=470, xaxis_title="Spindle speed (rpm)",
                          yaxis_title="Axial depth of cut ap (mm)",
                          yaxis_range=[0, max(top, s.ap_mm * 1.6)])
        st.plotly_chart(fig, width="stretch")
        st.caption("Below the curve the cut is stable. The pockets are the speeds where the "
                   "tooth passing frequency and its harmonics line up with the dominant mode, "
                   "so the regenerative effect cancels. Zero-order analytical solution "
                   "(Altintas & Budak), which assumes a rigid, constant-speed spindle and "
                   "linear cutting force coefficients. Process damping, which makes low-speed cuts "
                   "more stable than the diagram suggests, is not modelled.")

    # ---------------------------------------------------------------- roughness
    with tab_ra:
        left, right = st.columns([3, 2], gap="medium")
        with left:
            if s.operation.startswith("Ball"):
                x = np.linspace(s.stepover_mm * 0.2, s.stepover_mm * 2.5, 120)
                ys = [rg.roughness(s.operation, fz_mm=s.fz_mm, teeth=s.teeth,
                                   diameter_mm=s.diameter_mm, stepover_mm=v,
                                   process_factor=s.process_factor).ra_expected_um for v in x]
                xt, here = "Stepover (mm)", s.stepover_mm
            else:
                x = np.linspace(max(s.fz_mm * 0.15, 1e-5), s.fz_mm * 2.5, 120)
                ys = [rg.roughness(s.operation, fz_mm=v, teeth=s.teeth,
                                   diameter_mm=s.diameter_mm,
                                   nose_radius_mm=s.nose_radius_mm,
                                   runout_mm=s.runout_mm, process_factor=s.process_factor,
                                   edge_radius_um=s.edge_radius_um).ra_expected_um for v in x]
                xt, here = "Feed per tooth (mm)", s.fz_mm
            fig = go.Figure()
            fig.add_scatter(x=x, y=ys, name="Expected Ra",
                            line=dict(color=theme.SIGNAL, width=2))
            fig.add_scatter(x=[here], y=[rough.ra_expected_um], mode="markers",
                            name="Your setting", marker=dict(size=12, color=theme.INK))
            if s.target_ra_um:
                fig.add_hline(y=s.target_ra_um, line=dict(color=theme.DETAIL, dash="dash"),
                              annotation_text=f"target {s.target_ra_um:g} µm")
            fig.update_layout(height=400, xaxis_title=xt, yaxis_title="Ra (µm)")
            st.plotly_chart(fig, width="stretch")
        with right:
            st.markdown("**How the number is built**")
            rows = [("Geometric Ra", f"{rough.ra_geometric_um:.3f} µm"),
                    ("Geometric Rz", f"{rough.rz_geometric_um:.3f} µm"),
                    ("Mark spacing used", f"{rough.effective_feed_mm:.4f} mm")]
            rows += [(f"× {k}", f"{v:.2f}") for k, v in rough.factors.items()]
            rows.append(("Expected Ra", f"{rough.ra_expected_um:.3f} µm ({rough.grade})"))
            if rough.chatter_range_um:
                rows.append(("Under chatter",
                             f"{rough.chatter_range_um[0]:.1f}–{rough.chatter_range_um[1]:.1f} µm"))
            st.dataframe(pd.DataFrame(rows, columns=["", "Value"]), hide_index=True,
                         width="stretch")
        for note in rough.notes:
            st.caption(note)

    # ---------------------------------------------------------------- actions
    with tab_act:
        if not a.actions:
            st.success("Nothing to change — the condition is stable and meets the target.")
        for act in a.actions:
            with st.container(border=True):
                st.markdown(f"**{act.change}**")
                st.write(act.detail)
                if act.gain:
                    st.caption(act.gain)

    # ---------------------------------------------------------------- numbers
    with tab_num:
        modes = [("x", m) for m in s.dyn.x_modes] + [("y", m) for m in s.dyn.y_modes]
        st.dataframe(pd.DataFrame(
            [{"direction": d, "fn (Hz)": m.fn_hz, "ζ": m.zeta, "k (N/m)": m.k_n_m}
             for d, m in modes]), hide_index=True, width="stretch")
        axx, axy, ayx, ayy = dy.directional_coefficients(phi[0], phi[1], s.Kr)
        st.dataframe(pd.DataFrame([{
            "Kt (N/mm²)": s.Kt, "Kr": s.Kr, "teeth": s.teeth,
            "φ entry (°)": np.degrees(phi[0]), "φ exit (°)": np.degrees(phi[1]),
            "αxx": axx, "αxy": axy, "αyx": ayx, "αyy": ayy,
            "critical ap (mm)": float(np.min(res.alim_grid)),
            "ap limit here (mm)": a.ap_limit_mm,
        }]).T.rename(columns={0: "value"}), width="stretch")
        summary = pd.DataFrame([{
            "operation": s.operation, "D (mm)": s.diameter_mm, "teeth": s.teeth,
            "n (rpm)": s.n_rpm, "fz (mm)": s.fz_mm, "ap (mm)": s.ap_mm, "ae (mm)": s.ae_mm,
            "direction": s.direction, "feed (mm/min)": s.feed_mm_min,
            "vc (m/min)": s.cutting_speed_m_min, "ap limit (mm)": a.ap_limit_mm,
            "state": "chatter" if not a.stable else "stable", "margin": a.margin,
            "Ra expected (um)": rough.ra_expected_um, "grade": rough.grade,
            "MRR (mm3/min)": a.mrr_mm3_min}])
        st.download_button("Download this case as CSV", summary.to_csv(index=False).encode(),
                           file_name="rajmill_case.csv", mime="text/csv")
