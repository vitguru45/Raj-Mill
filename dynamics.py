"""Analytical chatter stability for milling.

Zero-order frequency-domain solution (Altintas & Budak, CIRP Annals 1995):
the time-varying directional coefficients are replaced by their average over one
tooth period, which turns the stability problem into an eigenvalue problem that
can be solved in closed form for each chatter frequency.

Conventions used throughout:
    phi_st, phi_ex   entry and exit angles, radians, measured from the +y axis
                     in the usual milling convention
    ap               axial depth of cut, mm
    ae               radial width of cut, mm
    n                spindle speed, rpm
    Kt, Kr           tangential cutting force coefficient (N/mm^2) and the
                     radial ratio Kr = Kn/Kt (dimensionless)

The module is framework-free: import it from a notebook or a script.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np


# --------------------------------------------------------------------------
# Machine / tool dynamics
# --------------------------------------------------------------------------

@dataclass
class Mode:
    """One vibration mode of the tool-holder-spindle system in one direction."""
    fn_hz: float          # natural frequency
    zeta: float           # damping ratio (0.03 = 3%)
    k_n_m: float          # modal stiffness, N/m

    def frf(self, omega: np.ndarray) -> np.ndarray:
        """Receptance, m/N. omega in rad/s."""
        wn = 2 * np.pi * self.fn_hz
        r = omega / wn
        return 1.0 / (self.k_n_m * (1 - r ** 2 + 2j * self.zeta * r))


@dataclass
class ToolDynamics:
    """Modes in the feed (x) and normal (y) directions."""
    x_modes: list[Mode]
    y_modes: list[Mode]

    def phi_xx(self, omega):
        return sum(m.frf(omega) for m in self.x_modes)

    def phi_yy(self, omega):
        return sum(m.frf(omega) for m in self.y_modes)

    @property
    def frequencies(self) -> list[float]:
        return [m.fn_hz for m in self.x_modes + self.y_modes]


# Presets so the app is usable before a tap test. These are representative
# figures for the classes of tool named, not measurements of a specific setup.
PRESETS: dict[str, dict] = {
    "Slender carbide end mill, long overhang": dict(
        fn=820.0, zeta=0.035, k=8.0e6, note="10-12 mm end mill, 4-5×D overhang"),
    "Short carbide end mill, rigid holder": dict(
        fn=1450.0, zeta=0.04, k=3.5e7, note="10-12 mm end mill, 2×D overhang"),
    "Face mill on a stiff spindle": dict(
        fn=600.0, zeta=0.05, k=5.0e7, note="50-63 mm face mill, machining centre"),
    "Micro end mill (0.5-1 mm), high-speed spindle": dict(
        fn=6500.0, zeta=0.03, k=1.2e6, note="tool-dominated mode, very low stiffness"),
    "Thin-walled workpiece (part-dominated)": dict(
        fn=380.0, zeta=0.015, k=4.0e6, note="flexible part, lightly damped"),
}


def preset_dynamics(name: str) -> ToolDynamics:
    p = PRESETS[name]
    mode = lambda: Mode(p["fn"], p["zeta"], p["k"])
    return ToolDynamics([mode()], [mode()])


# --------------------------------------------------------------------------
# Cut geometry
# --------------------------------------------------------------------------

def engagement_angles(diameter_mm: float, ae_mm: float, direction: str) -> tuple[float, float]:
    """Entry and exit angles for up (conventional) or down (climb) milling."""
    ratio = np.clip(ae_mm / diameter_mm, 1e-6, 1.0)
    if direction.startswith("up") or direction.startswith("conv"):
        return 0.0, float(np.arccos(1 - 2 * ratio))
    return float(np.arccos(2 * ratio - 1)), float(np.pi)


def directional_coefficients(phi_st: float, phi_ex: float, Kr: float):
    """Average directional factors alpha_xx, alpha_xy, alpha_yx, alpha_yy.

    These are the integrals of the time-varying directional matrix over one
    tooth period, evaluated in closed form between the entry and exit angles.
    """
    def evaluate(f):
        return f(phi_ex) - f(phi_st)

    axx = 0.5 * evaluate(lambda p: np.cos(2 * p) - 2 * Kr * p + Kr * np.sin(2 * p))
    axy = 0.5 * evaluate(lambda p: -np.sin(2 * p) - 2 * p + Kr * np.cos(2 * p))
    ayx = 0.5 * evaluate(lambda p: -np.sin(2 * p) + 2 * p + Kr * np.cos(2 * p))
    ayy = 0.5 * evaluate(lambda p: -np.cos(2 * p) - 2 * Kr * p - Kr * np.sin(2 * p))
    return axx, axy, ayx, ayy


# --------------------------------------------------------------------------
# Stability lobes
# --------------------------------------------------------------------------

@dataclass
class StabilityResult:
    speeds_rpm: np.ndarray            # one row per lobe number
    depths_mm: np.ndarray             # matching limiting axial depths
    lobes: np.ndarray                 # lobe index for each point
    chatter_hz: np.ndarray            # chatter frequency at each point
    n_grid: np.ndarray = field(default_factory=lambda: np.empty(0))
    alim_grid: np.ndarray = field(default_factory=lambda: np.empty(0))
    n_reliable_min: float = 0.0
    """Below this speed the lobes are closer together than the speed grid can
    resolve, so the envelope there is aliasing rather than physics. Low speeds
    are also where process damping makes real cuts more stable than this model
    predicts, so both effects say the same thing: do not trust it down there."""

    def limit_at(self, n_rpm: float) -> float:
        """Limiting depth of cut at one spindle speed, mm."""
        if self.n_grid.size == 0:
            return float("nan")
        return float(np.interp(n_rpm, self.n_grid, self.alim_grid))


def stability_lobes(dyn: ToolDynamics, *, teeth: int, Kt: float, Kr: float,
                    phi_st: float, phi_ex: float, n_lobes: int = 12,
                    freq_points: int = 6000,
                    freq_span: tuple[float, float] | None = None,
                    n_range: tuple[float, float] = (500, 30000),
                    n_points: int = 1200) -> StabilityResult:
    """Sweep chatter frequency, solve for the limiting depth and the speeds."""
    fns = dyn.frequencies
    lo, hi = freq_span or (0.35 * min(fns), 2.2 * max(fns))
    fc = np.linspace(max(1.0, lo), hi, freq_points)
    omega = 2 * np.pi * fc

    Pxx = dyn.phi_xx(omega)
    Pyy = dyn.phi_yy(omega)
    axx, axy, ayx, ayy = directional_coefficients(phi_st, phi_ex, Kr)

    # a0 * L^2 + a1 * L + 1 = 0
    a0 = Pxx * Pyy * (axx * ayy - axy * ayx)
    a1 = axx * Pxx + ayy * Pyy
    disc = np.sqrt(np.where(np.abs(a0) > 0, a1 ** 2 - 4 * a0, a1 ** 2 + 0j))

    speeds, depths, lobe_ids, freqs = [], [], [], []
    grid = np.linspace(n_range[0], n_range[1], n_points)
    branch_curves: list[np.ndarray] = []

    for sign in (+1, -1):                    # both roots of the quadratic
        with np.errstate(divide="ignore", invalid="ignore"):
            L = np.where(np.abs(a0) > 1e-30, (-a1 + sign * disc) / (2 * a0), -1.0 / a1)
        LR, LI = np.real(L), np.imag(L)
        kappa = LI / LR
        # Kt in N/mm^2 and receptance in m/N: the 1e-3 converts the depth to mm
        alim = -2 * np.pi * LR * (1 + kappa ** 2) / (teeth * Kt) * 1e-3
        eps = np.pi - 2 * np.arctan(kappa)
        for k in range(n_lobes + 1):
            T = (eps + 2 * np.pi * k) / omega          # tooth period, s
            n = 60.0 / (teeth * T)
            ok = (alim > 0) & np.isfinite(alim) & (n > n_range[0]) & (n < n_range[1])
            if ok.sum() < 3:
                continue
            speeds.append(n[ok]); depths.append(alim[ok])
            lobe_ids.append(np.full(ok.sum(), k)); freqs.append(fc[ok])
            branch_curves.append(_branch_on_grid(n[ok], alim[ok], grid))

    n_all = np.concatenate(speeds) if speeds else np.empty(0)
    a_all = np.concatenate(depths) if depths else np.empty(0)
    k_all = np.concatenate(lobe_ids) if lobe_ids else np.empty(0)
    f_all = np.concatenate(freqs) if freqs else np.empty(0)

    # The usable boundary is the lowest branch at each speed. Each branch is
    # interpolated onto the grid over the span it actually covers, so a sparsely
    # sampled branch cannot punch single-cell holes in the envelope.
    if branch_curves:
        stack = np.vstack(branch_curves)
        with warnings.catch_warnings():       # columns no branch covers are all-NaN
            warnings.simplefilter("ignore", RuntimeWarning)
            env = np.nanmin(stack, axis=0)
        env = _fill_gaps(np.where(np.isfinite(env), env, np.inf))
    else:
        env = np.zeros(n_points)
    step = grid[1] - grid[0]
    fn_min = min(dyn.frequencies)
    reliable = float(np.sqrt(20 * step * 60 * fn_min / teeth))
    return StabilityResult(speeds_rpm=n_all, depths_mm=a_all, lobes=k_all,
                           chatter_hz=f_all, n_grid=grid, alim_grid=env,
                           n_reliable_min=min(reliable, grid[-1]))


def _branch_on_grid(n: np.ndarray, a: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """One lobe branch resampled onto the speed grid, NaN outside its own span."""
    order = np.argsort(n)
    ns, as_ = n[order], a[order]
    # a branch can fold back on itself in speed; keep the lower depth per speed
    uniq, inv = np.unique(np.round(ns, 6), return_inverse=True)
    low = np.full(uniq.size, np.inf)
    np.minimum.at(low, inv, as_)
    out = np.interp(grid, uniq, low, left=np.nan, right=np.nan)
    return np.where((grid >= uniq[0]) & (grid <= uniq[-1]), out, np.nan)


def _fill_gaps(env: np.ndarray) -> np.ndarray:
    """Interpolate grid cells that no lobe point landed in."""
    finite = np.isfinite(env)
    if not finite.any():
        return np.zeros_like(env)
    idx = np.arange(len(env))
    return np.interp(idx, idx[finite], env[finite])


def chatter_frequency_at(res: StabilityResult, n_rpm: float) -> float:
    """Frequency the chatter would grow at, for the speed given."""
    if res.speeds_rpm.size == 0:
        return float("nan")
    near = np.abs(res.speeds_rpm - n_rpm) < max(25.0, 0.01 * n_rpm)
    if not near.any():
        near = np.abs(res.speeds_rpm - n_rpm) == np.abs(res.speeds_rpm - n_rpm).min()
    sel = np.argmin(res.depths_mm[near])
    return float(res.chatter_hz[near][sel])


# --------------------------------------------------------------------------
# Working with an operating point
# --------------------------------------------------------------------------

def tooth_passing_hz(n_rpm: float, teeth: int) -> float:
    return n_rpm * teeth / 60.0


def material_removal_rate(ap_mm: float, ae_mm: float, feed_mm_min: float) -> float:
    """MRR in mm^3/min."""
    return ap_mm * ae_mm * feed_mm_min


def stable_speed_suggestions(res: StabilityResult, ap_mm: float, n_rpm: float,
                             n_max: int = 3, margin: float = 1.2) -> list[dict]:
    """Speeds near the current one where the limit clears the depth being used.

    Returns the peak of each usable stability pocket, closest first.
    """
    n, a = res.n_grid, res.alim_grid
    usable = (a >= ap_mm * margin) & (n >= res.n_reliable_min)
    if not usable.any():
        return []
    # contiguous runs of usable speeds = stability pockets
    padded = np.r_[False, usable, False]
    starts = np.flatnonzero(~padded[:-1] & padded[1:])
    ends = np.flatnonzero(padded[:-1] & ~padded[1:]) - 1
    out = []
    step = n[1] - n[0]
    for s, e in zip(starts, ends):
        if e - s < 2:                       # ignore single-cell jitter
            continue
        best = s + int(np.argmax(a[s:e + 1]))
        nearest = int(np.clip(np.searchsorted(n, n_rpm), s, e))
        out.append({"speed_rpm": float(n[best]), "limit_mm": float(a[best]),
                    "nearest_rpm": float(n[nearest]),
                    "nearest_limit_mm": float(a[nearest]),
                    "from_rpm": float(n[s]), "to_rpm": float(n[e]),
                    "width_rpm": float(n[e] - n[s] + step),
                    "distance_rpm": float(abs(n[nearest] - n_rpm))})
    out.sort(key=lambda d: d["distance_rpm"])
    return out[:n_max]
