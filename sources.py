"""Where the models, the constants and the validation data come from."""
from __future__ import annotations

import streamlit as st


def render() -> None:
    st.markdown("#### About the model")
    st.markdown("""
- **No machine-learning model is used.** RajMill solves the chatter stability equations
  directly, so there is nothing trained, nothing fitted to a dataset, and no accuracy
  figure to quote. The same inputs always give the same answer, and every number in the
  verdict can be traced back to an equation.
- **Stability:** zero-order analytical solution in the frequency domain. The directional
  coefficients are averaged over one tooth period, and the resulting quadratic
  eigenvalue problem is solved at each chatter frequency to give the limiting axial
  depth and the lobe speeds.
- **Surface finish:** geometric roughness from the marks the tool leaves, then explicit
  factors for tool runout, minimum chip thickness (the ploughing regime in micro-milling)
  and a general process factor. Each factor is shown separately in the Roughness tab
  rather than folded into one number.
- **Recommendations:** computed, not canned. Suggested speeds are the peaks of stability
  pockets that the solver found, with their width in rpm; suggested feeds come from
  inverting the roughness equation for your target Ra.
- **Checks performed:** lobe speeds land at 60·fn/(N·k) as they should; the predicted
  chatter frequency sits just above the natural frequency; the critical depth rises as
  radial immersion falls (1.72 mm slotting, 4.54 mm at half immersion, 28.7 mm at 10%
  for the same system).
""")

    st.markdown("#### Method references")
    st.markdown("""
1. **Altintas, Y. and Budak, E.** (1995). Analytical prediction of stability lobes in
   milling. *CIRP Annals* 44(1), 357-362. The stability solution used here.
2. **Altintas, Y.** (2012). *Manufacturing Automation: Metal Cutting Mechanics, Machine
   Tool Vibrations, and CNC Design*, 2nd ed., Cambridge University Press. Cutting force
   coefficients, tap testing and the roughness geometry.
3. **Budak, E. and Altintas, Y.** (1998). Analytical prediction of chatter stability in
   milling, Parts I and II. *Journal of Dynamic Systems, Measurement, and Control* 120(1),
   22-36.
4. **Insperger, T. and Stepan, G.** (2011). *Semi-Discretization for Time-Delay Systems*,
   Springer. The method to reach for at low radial immersion and with variable-pitch
   cutters, which this app does not cover.
5. **Schmitz, T. L. and Smith, K. S.** (2019). *Machining Dynamics: Frequency Response to
   Improved Productivity*, 2nd ed., Springer. Tap testing, receptance coupling and
   process damping.
6. **ISO 1302** roughness grades N1 to N12, used to put a grade next to the predicted Ra.
""")

    st.markdown("#### Open datasets for checking the predictions")
    st.markdown("""
None of these are used to train anything - RajMill needs no training data. They are the
public recordings a student can use to test whether a prediction was right, and they are
where a chatter-detection project would start.

1. **i-CNC: vibration data with chatter indication during milling** (Zenodo, CC BY 4.0):
   [zenodo.org/records/15308467](https://zenodo.org/records/15308467)
   - X and Y accelerations at 10 kHz on two CNC machines, spindle speed logged alongside,
     each measurement tagged for chatter. About 3 GB, so take a subset.
2. **Turning dataset for chatter diagnosis using machine learning** (Mendeley Data):
   [doi.org/10.17632/hvm4wh3jzx.1](https://doi.org/10.17632/hvm4wh3jzx.1)
   - Two single-axis accelerometers, a triaxial accelerometer, a microphone and a laser
     tachometer, tagged no-chatter, intermediate chatter, chatter and unknown, at four
     stickout lengths. Turning rather than milling, but it is the set most chatter papers
     benchmark against, and the tagging procedure is documented.
3. **PHM 2010 data challenge: high-speed CNC milling cutter wear**
   ([phmsociety.org](https://phmsociety.org/phm_competition/2010-phm-society-conference-data-challenge/)):
   dynamometer, accelerometer and acoustic emission at 50 kHz with wear measurements.
4. **NASA milling data set** (Agogino and Goebel, NASA Prognostics Data Repository):
   [nasa.gov/.../pcoe-data-set-repository](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/)
   - Sixteen tools run to failure under eight conditions, with acoustic emission,
     vibration and current at 250 Hz. Useful for wear trends, too slow for chatter.
5. **Signal segmentation for milling process** (IEEE DataPort, open access):
   [ieee-dataport.org/open-access/signal-segmentation-milling-process](https://ieee-dataport.org/open-access/signal-segmentation-milling-process)
   - Three-axis spindle accelerometer in CSV at 2048 Hz, windowed and labelled dry run
     versus milling. Small files and a free login, so it is the easiest classroom start.
6. **MU-TCM face-milling dataset** (Mondragon Unibertsitatea, *Scientific Data* 2025):
   [doi.org/10.1038/s41597-025-05168-5](https://doi.org/10.1038/s41597-025-05168-5)
   - Cutting forces, vibration and acoustic emission with tool wear annotated before
     each experiment.
""")

    st.markdown("#### Constants used in the app")
    st.markdown("""
- **Cutting force coefficients (Kt, Kr)** in the material list are order-of-magnitude
  values for each material group. They change with tool geometry, coating, chip thickness
  and cutting speed, so calibrate them from your own force measurements before quoting a
  limiting depth to two decimal places.
- **Modal presets (fn, ζ, k)** are representative of the classes of tool named, not
  measurements of any particular machine. A tap test on your own spindle and tool takes
  ten minutes and replaces all of them.
""")

    st.markdown("#### Software")
    st.markdown("""
- [Streamlit](https://streamlit.io) for the web app, [Plotly](https://plotly.com/python/)
  for the charts
- [NumPy](https://numpy.org) and [SciPy](https://scipy.org) for the solver,
  [pandas](https://pandas.pydata.org) for the tables
- Machining guidance in the recommendations compiled from standard machining-dynamics
  practice for teaching use
""")
    st.caption("All referenced datasets and publications remain the property of their "
               "respective owners and are cited here only for teaching and "
               "non-commercial course purposes.")
