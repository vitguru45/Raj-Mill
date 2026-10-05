"""Ten verification cases for RajMill.

Run this in front of an audience: every row is computed by the same functions the
app calls, and each one has an independent check that can be done on paper or
argued from first principles.

    python demo_cases.py            # prints the table, writes rajmill_test_cases.csv
"""
from __future__ import annotations

import pandas as pd

from core import dynamics as dy
from core import roughness as rg

FACE = "Face milling / turning (nose radius)"
PERI = "Peripheral milling (flat end mill)"


def run(case):
    dyn = (dy.preset_dynamics(case["preset"]) if "preset" in case
           else dy.ToolDynamics([dy.Mode(*case["mode"])], [dy.Mode(*case["mode"])]))
    st_, ex = dy.engagement_angles(case["D"], case["ae"], case.get("dir", "down"))
    res = dy.stability_lobes(dyn, teeth=case["z"], Kt=case["Kt"], Kr=case.get("Kr", 0.3),
                             phi_st=st_, phi_ex=ex,
                             n_range=(max(200, case["n"] * 0.15), case["n"] * 3.5),
                             freq_points=9000)
    limit = res.limit_at(case["n"])
    stable = case["ap"] <= limit
    fc = None if stable else dy.chatter_frequency_at(res, case["n"])
    r = rg.roughness(case.get("op", FACE), fz_mm=case["fz"], teeth=case["z"],
                     diameter_mm=case["D"], nose_radius_mm=case.get("r_eps", 0.8),
                     runout_mm=case.get("runout", 0.0),
                     process_factor=case.get("pf", 1.8),
                     edge_radius_um=case.get("r_edge"), unstable=not stable)
    return {
        "#": case["id"],
        "What it shows": case["shows"],
        "n (rpm)": case["n"],
        "ap (mm)": case["ap"],
        "ae/D": round(case["ae"] / case["D"], 2),
        "fz (mm)": case["fz"],
        "ap limit (mm)": round(limit, 2),
        "Verdict": "CHATTER" if not stable else "stable",
        "Margin": round(limit / case["ap"], 2),
        "f_c (Hz)": None if fc is None else round(fc),
        "Ra (µm)": round(r.ra_expected_um, 3),
        "Independent check": case["check"],
    }


# fn = 600 Hz, 4 teeth -> lobe peaks at 60*600/(4k) = 9000, 4500, 3000 rpm
M600 = (600.0, 0.04, 3.5e7)

CASES = [
    dict(id=1, shows="Same depth, wrong speed", mode=M600, D=12, z=4, ae=12, ap=2.5,
         n=7000, fz=0.06, Kt=1800,
         check="7,000 rpm sits between lobes; expect chatter near fn = 600 Hz"),
    dict(id=2, shows="Same depth, right speed", mode=M600, D=12, z=4, ae=12, ap=2.5,
         n=9000, fz=0.06, Kt=1800,
         check="60·fn/(N·k) = 60·600/(4·1) = 9,000 rpm — the k=1 pocket"),
    dict(id=3, shows="Second pocket, same rule", mode=M600, D=12, z=4, ae=12, ap=2.5,
         n=4500, fz=0.06, Kt=1800,
         check="k=2 gives 4,500 rpm; a narrower pocket than k=1"),
    dict(id=4, shows="Slotting (100% immersion)", mode=M600, D=12, z=4, ae=12, ap=2.5,
         n=7000, fz=0.06, Kt=1800,
         check="Reference for cases 5-6: limit is lowest in a slot"),
    dict(id=5, shows="Half immersion", mode=M600, D=12, z=4, ae=6, ap=2.5, n=7000,
         fz=0.06, Kt=1800,
         check="Less time in cut per tooth, so the limit must rise above case 4"),
    dict(id=6, shows="10% immersion", mode=M600, D=12, z=4, ae=1.2, ap=2.5, n=7000,
         fz=0.06, Kt=1800,
         check="Limit must rise again; light radial cuts are far more stable"),
    dict(id=7, shows="Stiffness: long overhang",
         preset="Slender carbide end mill, long overhang", D=12, z=4, ae=3, ap=4.0,
         n=5000, fz=0.06, Kt=1800,
         check="k = 8 MN/m, fn = 820 Hz; low stiffness means a low limit"),
    dict(id=8, shows="Stiffness: short, rigid",
         preset="Short carbide end mill, rigid holder", D=12, z=4, ae=3, ap=4.0,
         n=5000, fz=0.06, Kt=1800,
         check="k = 35 MN/m and fn = 1,450 Hz; a stiffer, higher-frequency tool must lift the limit well clear of case 7"),
    dict(id=9, shows="Feed halved, Ra quartered", mode=M600, D=12, z=4, ae=6, ap=2.0,
         n=9000, fz=0.03, Kt=1800, r_eps=0.8,
         check="Ra = f²/(32r)·1.8 = 0.03²/(32·0.8)·1.8 = 0.063 µm; cases 1-8 at twice the feed give 0.253 µm, i.e. 4×"),
    dict(id=10, shows="Runout ruins the finish", mode=M600, D=12, z=4, ae=6, ap=2.0,
         n=9000, fz=0.03, Kt=1800, r_eps=0.8, runout=0.020,
         check="TIR 20 µm on fz 30 µm opens the marks to 0.09 mm, so Ra must rise by (0.09/0.03)² = 9× to 0.57 µm"),
]

if __name__ == "__main__":
    df = pd.DataFrame([run(c) for c in CASES])
    pd.set_option("display.width", 200, "display.max_columns", 50)
    print(df.to_string(index=False))
    df.to_csv("rajmill_test_cases.csv", index=False)
    print("\nWritten: rajmill_test_cases.csv")
