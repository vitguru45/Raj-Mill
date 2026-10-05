"""Turn the stability and roughness results into a verdict and a set of moves.

Every recommendation here is computed from the models — a suggested spindle
speed comes from the stability pockets that were actually solved for, and a
suggested feed comes from inverting the roughness model — rather than being a
fixed list of machining advice.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import dynamics as dy
from . import roughness as rg


@dataclass
class Action:
    change: str
    detail: str
    gain: str = ""


@dataclass
class Assessment:
    stable: bool
    margin: float                 # ap_limit / ap, above 1 is stable
    ap_limit_mm: float
    chatter_hz: float | None
    tooth_passing_hz: float
    meets_target: bool | None
    headline: str
    state_reason: str
    finish_reason: str
    actions: list[Action] = field(default_factory=list)
    mrr_mm3_min: float = 0.0


def assess(*, res: dy.StabilityResult, ap_mm: float, ae_mm: float, n_rpm: float,
           teeth: int, fz_mm: float, feed_mm_min: float,
           rough: rg.RoughnessResult, target_ra_um: float | None,
           operation: str, diameter_mm: float, nose_radius_mm: float,
           process_factor: float, dyn: dy.ToolDynamics, Kt: float, Kr: float,
           direction: str) -> Assessment:
    ap_limit = res.limit_at(n_rpm)
    stable = ap_mm <= ap_limit
    margin = ap_limit / max(ap_mm, 1e-9)
    tpf = dy.tooth_passing_hz(n_rpm, teeth)
    fc = None if stable else dy.chatter_frequency_at(res, n_rpm)

    if stable:
        state_reason = (
            f"At {n_rpm:,.0f} rpm the limiting axial depth is {ap_limit:.2f} mm and you "
            f"are cutting {ap_mm:.2f} mm, so the cut sits {margin:.1f}× inside the "
            "stability boundary.")
        if margin < 1.3:
            state_reason += (" That is a thin margin — a worn tool or a softer clamping "
                             "will push it over.")
    else:
        state_reason = (
            f"At {n_rpm:,.0f} rpm the limiting axial depth is {ap_limit:.2f} mm but you "
            f"are cutting {ap_mm:.2f} mm, which is {1 / max(margin, 1e-9):.1f}× the limit. "
            f"Regenerative chatter is predicted at about {fc:,.0f} Hz, against a tooth "
            f"passing frequency of {tpf:,.0f} Hz.")

    meets = None if target_ra_um is None else rough.ra_expected_um <= target_ra_um
    if target_ra_um is None:
        finish_reason = (f"Expected Ra is about {rough.ra_expected_um:.2f} µm "
                         f"({rough.grade}), from a geometric {rough.ra_geometric_um:.2f} µm.")
    elif meets:
        finish_reason = (f"Expected Ra {rough.ra_expected_um:.2f} µm meets the "
                         f"{target_ra_um:.2f} µm target with room to spare.")
    else:
        finish_reason = (f"Expected Ra {rough.ra_expected_um:.2f} µm misses the "
                         f"{target_ra_um:.2f} µm target by "
                         f"{rough.ra_expected_um / target_ra_um:.1f}×.")

    quality = "bad" if meets is False else "good"
    headline = {
        (True, "good"): "Stable cut, finish within target",
        (True, "bad"): "Stable cut, but the finish misses the target",
        (False, "good"): "Chatter predicted — the finish figure will not hold",
        (False, "bad"): "Chatter predicted, and the finish misses the target",
    }[(stable, quality)]

    actions = _actions(res=res, ap_mm=ap_mm, ae_mm=ae_mm, n_rpm=n_rpm, teeth=teeth,
                       fz_mm=fz_mm, stable=stable, rough=rough,
                       target_ra_um=target_ra_um, operation=operation,
                       diameter_mm=diameter_mm, nose_radius_mm=nose_radius_mm,
                       process_factor=process_factor, dyn=dyn, Kt=Kt, Kr=Kr,
                       direction=direction, feed_mm_min=feed_mm_min)

    return Assessment(stable=stable, margin=float(margin), ap_limit_mm=float(ap_limit),
                      chatter_hz=fc, tooth_passing_hz=tpf, meets_target=meets,
                      headline=headline, state_reason=state_reason,
                      finish_reason=finish_reason, actions=actions,
                      mrr_mm3_min=dy.material_removal_rate(ap_mm, ae_mm, feed_mm_min))


def _actions(*, res, ap_mm, ae_mm, n_rpm, teeth, fz_mm, stable, rough, target_ra_um,
             operation, diameter_mm, nose_radius_mm, process_factor, dyn, Kt, Kr,
             direction, feed_mm_min) -> list[Action]:
    out: list[Action] = []

    if not stable:
        pockets = dy.stable_speed_suggestions(res, ap_mm, n_rpm)
        for p in pockets[:2]:
            new_feed = p["speed_rpm"] * teeth * fz_mm
            out.append(Action(
                change=f"Move the spindle to {p['speed_rpm']:,.0f} rpm",
                detail=(f"That pocket runs from {p['from_rpm']:,.0f} to "
                        f"{p['to_rpm']:,.0f} rpm and allows {p['limit_mm']:.2f} mm "
                        f"axial depth at its peak, against the {ap_mm:.2f} mm you need. "
                        f"Keep the feed per tooth: feed becomes {new_feed:,.0f} mm/min."),
                gain=f"{p['width_rpm']:,.0f} rpm wide, so it tolerates speed drift"))
        if not pockets:
            out.append(Action(
                change="No stable pocket at this depth anywhere in the speed range",
                detail="The depth of cut is above the critical limit at every speed, so "
                       "no choice of spindle speed will fix it on its own.",
                gain=""))

        out.append(Action(
            change=f"Reduce axial depth to {res.limit_at(n_rpm) / 1.3:.2f} mm at this speed",
            detail=(f"The limit here is {res.limit_at(n_rpm):.2f} mm; taking 30% below it "
                    "leaves margin for tool wear. Two passes at that depth beat one "
                    "chattered pass."),
            gain=f"Keeps {n_rpm:,.0f} rpm if the speed is fixed by the setup"))

        lighter = _limit_at_lower_immersion(dyn, teeth, Kt, Kr, diameter_mm, ae_mm,
                                            direction, n_rpm)
        if lighter and lighter[1] > res.limit_at(n_rpm) * 1.15:
            out.append(Action(
                change=f"Reduce radial engagement to {lighter[0]:.2f} mm",
                detail=(f"Lighter radial immersion raises the limit at this speed from "
                        f"{res.limit_at(n_rpm):.2f} to {lighter[1]:.2f} mm, because the "
                        "tooth spends less time in the cut."),
                gain="Often recovers the lost material rate through higher feed"))

        out.append(Action(
            change="If the speed is fixed, change the cutter or add damping",
            detail="A variable-pitch or variable-helix cutter breaks the regenerative "
                   "phasing that this analysis assumes. A shorter overhang raises the "
                   "natural frequency and the stiffness, which lifts the whole diagram.",
            gain="Shifts the boundary rather than working around it"))

    # Finish
    if target_ra_um is not None and rough.ra_expected_um > target_ra_um:
        if operation.startswith("Ball"):
            ae_new = rg.stepover_for_target_ra(target_ra_um, diameter_mm, process_factor)
            out.append(Action(
                change=f"Reduce the stepover to about {ae_new:.3f} mm",
                detail="Ball-nose finish is set by the scallop between passes, so "
                       "stepover is the lever, not feed.",
                gain=f"Roughly {ae_mm / max(ae_new, 1e-6):.1f}× more passes"))
        else:
            fz_new = rg.feed_for_target_ra(operation, target_ra_um, teeth=teeth,
                                           diameter_mm=diameter_mm,
                                           nose_radius_mm=nose_radius_mm,
                                           process_factor=process_factor)
            if fz_new:
                out.append(Action(
                    change=f"Reduce feed per tooth to about {fz_new:.4f} mm",
                    detail=(f"Ra scales with the square of the feed, so going from "
                            f"{fz_mm:.4f} to {fz_new:.4f} mm/tooth brings the expected "
                            f"value to the {target_ra_um:.2f} µm target. Stability is "
                            "unaffected: the lobe diagram does not depend on feed."),
                    gain=f"Feed rate becomes {n_rpm * teeth * fz_new:,.0f} mm/min"))
        if operation.startswith("Face"):
            r_new = nose_radius_mm * (rough.ra_expected_um / target_ra_um)
            out.append(Action(
                change=f"Or fit a larger nose radius, about {r_new:.2f} mm",
                detail="Ra falls inversely with nose radius, so a bigger radius or a "
                       "wiper insert meets the target without losing feed rate.",
                gain="Keeps the material removal rate"))

    if "ploughing" in rough.factors:
        out.append(Action(
            change="Raise feed per tooth above the minimum chip thickness",
            detail="Below roughly a quarter of the edge radius the edge rubs rather "
                   "than cuts, which raises roughness, forces and tool wear at the same "
                   "time. Counter-intuitively, feeding harder gives a better finish here.",
            gain="Also reduces the risk of tool breakage in micro-milling"))

    if "runout" in rough.factors:
        out.append(Action(
            change="Check and correct tool runout",
            detail=(f"Runout is spreading the marks to {rough.effective_feed_mm:.4f} mm "
                    f"instead of {fz_mm:.4f} mm, which is the same as multiplying the "
                    "feed. Re-seat the tool, clean the taper, or measure TIR with a dial "
                    "indicator."),
            gain="Recovers finish without changing any cutting parameter"))

    if stable and (target_ra_um is None or rough.ra_expected_um <= target_ra_um):
        headroom = res.limit_at(n_rpm) / max(ap_mm, 1e-9)
        out.append(Action(
            change=f"There is headroom: the limit here is {res.limit_at(n_rpm):.2f} mm",
            detail=(f"You are using {ap_mm:.2f} mm, which is {headroom:.1f}× inside the "
                    "boundary. Raising the depth in steps, checking the surface each "
                    "time, converts that margin into material rate."),
            gain=f"Up to {(headroom / 1.3):.1f}× the current MRR while keeping margin"))

    return out


def _limit_at_lower_immersion(dyn, teeth, Kt, Kr, diameter_mm, ae_mm, direction,
                              n_rpm) -> tuple[float, float] | None:
    """Re-solve the diagram at half the radial width and report the new limit."""
    ae_new = max(ae_mm / 2, diameter_mm * 0.02)
    if ae_new >= ae_mm:
        return None
    st, ex = dy.engagement_angles(diameter_mm, ae_new, direction)
    res = dy.stability_lobes(dyn, teeth=teeth, Kt=Kt, Kr=Kr, phi_st=st, phi_ex=ex,
                             freq_points=2500, n_points=800,
                             n_range=(max(200, n_rpm * 0.2), n_rpm * 3))
    return ae_new, res.limit_at(n_rpm)
