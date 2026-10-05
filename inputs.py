"""The sidebar form, in one place so every page asks for the same things.

Cutting force coefficients are order-of-magnitude values for the material
groups named. They vary with tool geometry, coating, chip thickness and speed,
so replace them with your own calibrated values when you have them.
"""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from . import dynamics as dy
from . import roughness as rg

MATERIALS = {
    "Aluminium 6061 / 7075": dict(Kt=750.0, Kr=0.30),
    "Brass / bronze": dict(Kt=700.0, Kr=0.28),
    "Cast iron": dict(Kt=1100.0, Kr=0.30),
    "Mild steel 1018 / 1045": dict(Kt=1800.0, Kr=0.35),
    "Alloy steel 4140, hardened": dict(Kt=2300.0, Kr=0.38),
    "Stainless 304 / 316": dict(Kt=2000.0, Kr=0.40),
    "Ti-6Al-4V": dict(Kt=1700.0, Kr=0.35),
    "Inconel 718": dict(Kt=2600.0, Kr=0.42),
    "Custom": dict(Kt=1500.0, Kr=0.35),
}


@dataclass
class Setup:
    operation: str
    diameter_mm: float
    teeth: int
    nose_radius_mm: float
    edge_radius_um: float | None
    ae_mm: float
    ap_mm: float
    n_rpm: float
    fz_mm: float
    direction: str
    Kt: float
    Kr: float
    dyn: dy.ToolDynamics
    runout_mm: float
    process_factor: float
    target_ra_um: float | None
    stepover_mm: float

    @property
    def feed_mm_min(self) -> float:
        return self.n_rpm * self.teeth * self.fz_mm

    @property
    def cutting_speed_m_min(self) -> float:
        return 3.141592653589793 * self.diameter_mm * self.n_rpm / 1000.0

    @property
    def angles(self):
        return dy.engagement_angles(self.diameter_mm, self.ae_mm, self.direction)


def sidebar() -> Setup:
    with st.sidebar:
        st.header("Operation")
        operation = st.selectbox("Type", rg.OPERATIONS)

        st.header("Tool")
        c1, c2 = st.columns(2)
        diameter = c1.number_input("Diameter (mm)", 0.05, 300.0, 12.0, 0.5)
        teeth = int(c2.number_input("Teeth", 1, 20, 4, 1))
        nose = st.number_input("Nose radius (mm)", 0.0, 10.0, 0.8, 0.1,
                               help="Used by the roughness model for face milling "
                                    "and turning.")
        micro = st.checkbox("Micro tool — account for minimum chip thickness",
                            value=diameter < 2.0)
        edge_radius = st.number_input("Cutting-edge radius (µm)", 0.1, 50.0, 2.0, 0.5) \
            if micro else None

        st.header("Cut")
        c1, c2 = st.columns(2)
        ap = c1.number_input("Axial depth ap (mm)", 0.001, 100.0, 4.0, 0.5)
        ae = c2.number_input("Radial width ae (mm)", 0.001, 300.0, 3.0, 0.5)
        if ae > diameter:
            st.warning("Radial width is larger than the cutter; treating it as slotting.")
            ae = diameter
        c1, c2 = st.columns(2)
        n_rpm = c1.number_input("Spindle speed (rpm)", 10.0, 200000.0, 5000.0, 100.0)
        fz = c2.number_input("Feed per tooth (mm)", 0.00005, 2.0, 0.06, 0.01,
                             format="%.5f")
        direction = st.radio("Milling direction", ["down (climb)", "up (conventional)"],
                             horizontal=True)
        stepover = st.number_input("Stepover for finishing (mm)", 0.001, 50.0, 0.5, 0.1) \
            if operation.startswith("Ball") else 0.5

        st.header("Workpiece")
        mat = st.selectbox("Material", list(MATERIALS))
        d = MATERIALS[mat]
        c1, c2 = st.columns(2)
        Kt = c1.number_input("Kt (N/mm²)", 100.0, 6000.0, float(d["Kt"]), 50.0)
        Kr = c2.number_input("Kr = Kn/Kt", 0.0, 1.5, float(d["Kr"]), 0.05)

        st.header("Dynamics")
        preset = st.selectbox("Tap-test data", list(dy.PRESETS) + ["Enter my own"])
        if preset == "Enter my own":
            st.caption("From a tap test: natural frequency, damping ratio and modal "
                       "stiffness of the dominant mode in each direction.")
            c1, c2, c3 = st.columns(3)
            fx = c1.number_input("fn x (Hz)", 10.0, 50000.0, 800.0, 10.0)
            zx = c2.number_input("ζ x", 0.001, 0.5, 0.035, 0.005, format="%.3f")
            kx = c3.number_input("k x (N/m)", 1e4, 1e9, 1.0e7, 1e6, format="%.3g")
            same = st.checkbox("y direction is the same", value=True)
            if same:
                fy, zy, ky = fx, zx, kx
            else:
                c1, c2, c3 = st.columns(3)
                fy = c1.number_input("fn y (Hz)", 10.0, 50000.0, 900.0, 10.0)
                zy = c2.number_input("ζ y", 0.001, 0.5, 0.035, 0.005, format="%.3f")
                ky = c3.number_input("k y (N/m)", 1e4, 1e9, 1.2e7, 1e6, format="%.3g")
            dyn = dy.ToolDynamics([dy.Mode(fx, zx, kx)], [dy.Mode(fy, zy, ky)])
        else:
            st.caption(dy.PRESETS[preset]["note"] + " — representative values, "
                       "not a measurement of your machine.")
            dyn = dy.preset_dynamics(preset)

        st.header("Finish")
        runout = st.number_input("Tool runout, TIR (µm)", 0.0, 500.0, 0.0, 1.0) / 1000.0
        factor = st.slider("Process factor", 1.0, 3.5, 1.8, 0.1,
                           help="How much above the geometric value real Ra lands. "
                                "1.5–2.5 is typical for a healthy cut.")
        use_target = st.checkbox("I have a target Ra", value=True)
        target = st.number_input("Target Ra (µm)", 0.01, 50.0, 1.6, 0.1) \
            if use_target else None

    return Setup(operation=operation, diameter_mm=diameter, teeth=teeth,
                 nose_radius_mm=nose, edge_radius_um=edge_radius, ae_mm=ae, ap_mm=ap,
                 n_rpm=n_rpm, fz_mm=fz, direction="down" if direction.startswith("down")
                 else "up", Kt=Kt, Kr=Kr, dyn=dyn, runout_mm=runout,
                 process_factor=factor, target_ra_um=target, stepover_mm=stepover)


@st.cache_data(show_spinner=False)
def solve(dyn_key_: tuple, teeth: int, Kt: float, Kr: float, phi: tuple[float, float],
          n_range: tuple[float, float], _dyn: dy.ToolDynamics) -> dy.StabilityResult:
    """Cached stability solve.

    dyn_key_ carries the modal numbers so the cache sees changes in tool dynamics;
    _dyn (leading underscore) is the unhashable object and is skipped by the cache.
    """
    return dy.stability_lobes(_dyn, teeth=teeth, Kt=Kt, Kr=Kr,
                              phi_st=phi[0], phi_ex=phi[1], n_range=n_range)


def dyn_key(dyn: dy.ToolDynamics) -> tuple:
    return tuple((m.fn_hz, m.zeta, m.k_n_m) for m in dyn.x_modes + dyn.y_modes)


def speed_range(s: Setup) -> tuple[float, float]:
    top = max(s.n_rpm * 2.5, max(m.fn_hz for m in s.dyn.x_modes) * 60 / s.teeth * 1.5)
    return (max(100.0, s.n_rpm * 0.15), float(min(top, 300000)))
