"""Expected surface roughness from the cutting geometry.

The geometric part is exact: it is the height of the material left between
successive tool marks. The rest is honest correction factors, each one reported
separately so you can see what the number is made of rather than trusting a
single figure.

Real Ra is almost always above the geometric value — tool wear, built-up edge,
side flow, runout and residual vibration all add to it. A process factor of
about 1.5 to 2.5 is typical for a well-behaved cut.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# ISO 1302 roughness grades, Ra in micrometres
ISO_GRADES = {"N1": 0.025, "N2": 0.05, "N3": 0.1, "N4": 0.2, "N5": 0.4, "N6": 0.8,
              "N7": 1.6, "N8": 3.2, "N9": 6.3, "N10": 12.5, "N11": 25.0, "N12": 50.0}

OPERATIONS = ["Face milling / turning (nose radius)",
              "Peripheral milling (flat end mill)",
              "Ball-nose finishing (stepover)"]


@dataclass
class RoughnessResult:
    ra_geometric_um: float
    ra_expected_um: float
    rz_geometric_um: float
    effective_feed_mm: float
    factors: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    chatter_range_um: tuple[float, float] | None = None

    @property
    def grade(self) -> str:
        for name, value in ISO_GRADES.items():
            if self.ra_expected_um <= value:
                return name
        return "coarser than N12"


def effective_feed(fz_mm: float, teeth: int, runout_mm: float) -> tuple[float, float]:
    """Feed between consecutive marks once runout is accounted for.

    With no runout every tooth cuts the same chip and the marks are fz apart.
    Once the radial throw of one tooth exceeds the feed per tooth, that tooth
    does all the cutting and the marks open out towards the feed per revolution.
    """
    if runout_mm <= 0 or teeth <= 1:
        return fz_mm, 0.0
    share = float(min(1.0, runout_mm / max(fz_mm, 1e-9)))
    return fz_mm * (1 + share * (teeth - 1)), share


def roughness(operation: str, *, fz_mm: float, teeth: int, diameter_mm: float,
              nose_radius_mm: float = 0.8, stepover_mm: float = 0.5,
              runout_mm: float = 0.0, process_factor: float = 1.8,
              edge_radius_um: float | None = None,
              unstable: bool = False) -> RoughnessResult:
    f_eff, runout_share = effective_feed(fz_mm, teeth, runout_mm)
    notes: list[str] = []
    factors: dict[str, float] = {}

    if operation.startswith("Face"):
        rz = f_eff ** 2 / (8 * max(nose_radius_mm, 1e-6)) * 1e3     # mm -> um
        ra = f_eff ** 2 / (32 * max(nose_radius_mm, 1e-6)) * 1e3
        notes.append("Geometric part: marks left by the nose radius, "
                     "Rz = f²/(8r), Ra = f²/(32r).")
    elif operation.startswith("Peripheral"):
        R = max(diameter_mm / 2, 1e-6)
        rz = f_eff ** 2 / (8 * R) * 1e3
        ra = rz / 4
        notes.append("Geometric part: cusps left by the circular tooth path on the "
                     "wall, Rz ≈ fz²/(8R) with R the cutter radius.")
    else:
        R = max(diameter_mm / 2, 1e-6)
        h = R - np.sqrt(max(R ** 2 - (stepover_mm / 2) ** 2, 0.0))
        rz = h * 1e3
        ra = rz / 4
        notes.append("Geometric part: scallop height between passes, "
                     "h = R − √(R² − (ae/2)²). Stepover drives this, not feed.")

    ra_expected = ra
    if runout_share > 0:
        factors["runout"] = f_eff / max(fz_mm, 1e-9)
        notes.append(f"Runout of {runout_mm * 1000:.0f} µm opens the mark spacing from "
                     f"{fz_mm:.4f} to {f_eff:.4f} mm/mark.")

    # Minimum chip thickness: below roughly a quarter of the edge radius the
    # edge ploughs instead of cutting, and the finish degrades sharply. This
    # matters in micro-milling, where fz and the edge radius are comparable.
    if edge_radius_um:
        h_min_mm = 0.25 * edge_radius_um * 1e-3
        if fz_mm < h_min_mm:
            k = float(np.sqrt(h_min_mm / max(fz_mm, 1e-9)))
            factors["ploughing"] = k
            ra_expected *= k
            notes.append(
                f"Feed per tooth ({fz_mm * 1000:.1f} µm) is below the minimum chip "
                f"thickness (~{h_min_mm * 1000:.1f} µm for a {edge_radius_um:.0f} µm "
                "edge radius), so the edge ploughs and rubs. Heuristic penalty applied.")

    factors["process"] = process_factor
    ra_expected *= process_factor

    chatter_range = None
    if unstable:
        chatter_range = (ra_expected * 3, ra_expected * 10)
        notes.append("The cut is predicted to be unstable, so this figure is only a "
                     "floor: chatter marks set the finish instead of the feed marks. "
                     "Measured Ra under chatter is typically three to ten times the "
                     "stable value, with visible waviness.")

    return RoughnessResult(ra_geometric_um=float(ra), ra_expected_um=float(ra_expected),
                           rz_geometric_um=float(rz), effective_feed_mm=float(f_eff),
                           factors=factors, notes=notes, chatter_range_um=chatter_range)


def feed_for_target_ra(operation: str, target_ra_um: float, *, teeth: int,
                       diameter_mm: float, nose_radius_mm: float,
                       process_factor: float) -> float | None:
    """Feed per tooth that would just meet a target Ra, ignoring runout."""
    ra = target_ra_um / max(process_factor, 1e-6)
    if operation.startswith("Face"):
        return float(np.sqrt(ra * 32 * nose_radius_mm * 1e-3))
    if operation.startswith("Peripheral"):
        return float(np.sqrt(ra * 4 * 8 * (diameter_mm / 2) * 1e-3))
    return None            # ball-nose finish is set by stepover, not feed


def stepover_for_target_ra(target_ra_um: float, diameter_mm: float,
                           process_factor: float) -> float:
    """Stepover that would just meet a target Ra in ball-nose finishing."""
    R = diameter_mm / 2
    h = target_ra_um / max(process_factor, 1e-6) * 4 * 1e-3      # um -> mm
    h = min(h, R * 0.999)
    return float(2 * np.sqrt(max(R ** 2 - (R - h) ** 2, 0.0)))
