"""What the app does with your numbers, and where it stops being trustworthy."""
from __future__ import annotations

import streamlit as st

STEPS = [
    ("Tool dynamics",
     "Natural frequency, damping ratio and modal stiffness in the feed and normal "
     "directions, from your tap test or from one of the presets."),
    ("Stability limit",
     "The directional coefficients are averaged over one tooth period, which turns the "
     "delay-differential problem into a quadratic eigenvalue problem. Solving it at each "
     "chatter frequency gives the limiting axial depth and the spindle speeds of every "
     "lobe."),
    ("Surface finish",
     "The geometric marks left by the feed and the nose radius, then separate correction "
     "factors for tool runout, minimum chip thickness and general process effects."),
    ("What to change",
     "Suggested speeds come from the stability pockets that were actually solved for, "
     "and suggested feeds from inverting the roughness equation. Nothing here is a "
     "fixed list of advice."),
]


def render() -> None:
    st.markdown("#### From your numbers to the verdict")
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    for col, (i, (title, body)) in zip(st.columns(4, gap="medium"), enumerate(STEPS, 1)):
        with col:
            st.markdown(f'<div class="step-num">{i}</div>', unsafe_allow_html=True)
            st.markdown(f"**{title}**")
            st.caption(body)

    st.markdown("#### Symbols")
    with st.expander("What each variable means", expanded=False):
        st.markdown("""
**You type these in**

| Symbol | Name | Unit | What it is |
|---|---|---|---|
| D | Cutter diameter | mm | Diameter of the tool |
| N or z | Number of teeth | – | Flutes or inserts doing the cutting |
| n | Spindle speed | rpm | Revolutions per minute |
| a<sub>p</sub> | Axial depth of cut | mm | Depth along the tool axis — the one chatter cares about |
| a<sub>e</sub> | Radial width of cut | mm | Sideways engagement; a<sub>e</sub>/D is the immersion |
| f<sub>z</sub> | Feed per tooth | mm/tooth | Chip advance per tooth; sets the finish |
| r<sub>ε</sub> | Nose radius | mm | Corner radius of the insert |
| r<sub>e</sub> | Edge radius | µm | Sharpness of the cutting edge; matters in micro-milling |
| K<sub>t</sub> | Tangential cutting force coefficient | N/mm² | Force per unit chip area; a material property in practice |
| K<sub>r</sub> | Radial force ratio | – | K<sub>n</sub>/K<sub>t</sub>, how much force pushes sideways |
| f<sub>n</sub> | Natural frequency | Hz | From a tap test, per direction |
| ζ | Damping ratio | – | From the same tap test; 0.03 means 3% |
| k | Modal stiffness | N/m | Force needed per metre of deflection |
| TIR | Tool runout | µm | Radial throw of one tooth relative to the others |

**The app works these out**

| Symbol | Name | Unit | What it is |
|---|---|---|---|
| a<sub>lim</sub> | Limiting axial depth | mm | Deepest stable cut at that spindle speed |
| margin | a<sub>lim</sub>/a<sub>p</sub> | – | Above 1 is stable; 1.3 or more is a working margin |
| f<sub>c</sub> | Chatter frequency | Hz | Frequency the vibration would grow at, near f<sub>n</sub> |
| f<sub>TP</sub> | Tooth passing frequency | Hz | n·N/60; the forcing frequency of the cut |
| v<sub>c</sub> | Cutting speed | m/min | π·D·n/1000 |
| f | Feed rate | mm/min | n·N·f<sub>z</sub> |
| MRR | Material removal rate | mm³/min | a<sub>p</sub>·a<sub>e</sub>·f |
| R<sub>a</sub> | Arithmetic mean roughness | µm | Average height deviation of the surface |
| R<sub>z</sub> | Peak-to-valley height | µm | Roughly 4·R<sub>a</sub> for feed marks |
| k | Lobe number | – | 0, 1, 2… one waviness cycle more per tooth period |

**Inside the equations**

| Symbol | Name | What it is |
|---|---|---|
| Φ(iω) | Receptance, FRF | Deflection per unit force at frequency ω, from f<sub>n</sub>, ζ and k |
| α | Directional coefficients | Directional factors averaged over one tooth period |
| φ<sub>st</sub>, φ<sub>ex</sub> | Entry and exit angles | Where the tooth enters and leaves the cut, set by a<sub>e</sub>/D |
| Λ | Eigenvalue | Complex root of the characteristic equation; Λ<sub>R</sub> gives a<sub>lim</sub> |
| κ | Λ<sub>I</sub>/Λ<sub>R</sub> | Ratio that fixes the phase, and so the lobe speeds |
| ε | Phase shift | Between successive wavy surfaces; ε = π − 2·arctan κ |
| T | Tooth period | Time between one tooth and the next, 60/(n·N) |
""", unsafe_allow_html=True)

    st.markdown("#### The equations")
    st.markdown(
        "Stability, after Altintas and Budak (1995). With the averaged directional "
        "coefficients α and the receptances Φ:")
    st.latex(r"a_0\Lambda^2 + a_1\Lambda + 1 = 0")
    st.latex(r"a_{lim} = -\frac{2\pi\Lambda_R}{N\,K_t}\left(1+\kappa^2\right),"
             r"\qquad \kappa = \frac{\Lambda_I}{\Lambda_R}")
    st.latex(r"\varepsilon = \pi - 2\tan^{-1}\kappa, \qquad "
             r"T = \frac{\varepsilon + 2k\pi}{\omega_c}, \qquad n = \frac{60}{N\,T}")
    st.markdown("Surface finish, from the geometry of the marks left behind:")
    st.latex(r"R_z = \frac{f^2}{8r_\varepsilon}, \qquad R_a = \frac{f^2}{32 r_\varepsilon}"
             r"\qquad\text{(nose radius)}")
    st.latex(r"R_z \approx \frac{f_z^2}{8R} \quad\text{(end-milled wall)}, \qquad "
             r"h = R - \sqrt{R^2 - (a_e/2)^2} \quad\text{(ball-nose scallop)}")

    st.markdown("#### What the model assumes")
    st.markdown(
        "- A regular-pitch cutter, constant spindle speed and linear cutting force "
        "coefficients\n"
        "- A rigid workpiece whose dynamics do not change as material comes off\n"
        "- Directional factors averaged over the tooth period, which is accurate at "
        "moderate to high radial immersion\n"
        "- Roughness set by the feed marks, with wear, built-up edge and side flow "
        "lumped into one process factor")

    st.markdown("#### Where it stops")
    st.markdown(
        "- **Very low radial immersion and variable-pitch cutters.** Extra lobes appear "
        "that the averaged model cannot see. Semi-discretisation or a time-domain "
        "simulation is the right tool there.\n"
        "- **Low spindle speeds.** Process damping, where the flank rubs against the "
        "wavy surface, makes real cuts more stable than this predicts. That band is "
        "greyed out in the diagrams.\n"
        "- **The inputs, not the equations.** Modal parameters and cutting force "
        "coefficients dominate the answer. The presets are representative of classes "
        "of tool and material, not measurements of your machine.")
    st.caption("A teaching and planning aid, not a certified process guarantee. Confirm "
               "on the machine with a light test cut before committing a part.")
