# RajMill

Predicts whether a milling condition will chatter, what surface roughness to
expect, and what to change if the answer is bad. Pure Python: Streamlit for the
interface, NumPy and SciPy for the models.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501.

Built for course use at CIMR-VIT, in the same house style as Raj3DLabs: one `app.py`,
a `SETTINGS` block at the top for the site name, tagline and credit line, and a Sources
tab at the end covering the model, the references and the open datasets.

## Tabs

- **Predict my cut** — enter tool, material, cutting parameters and tool dynamics; get a
  stable/chatter verdict with margin, the expected Ra and grade, the stability lobe
  diagram with your operating point on it, and a list of changes with numbers attached.
- **Process map** — the same model swept over speed and depth, drawn as a margin map,
  with the most productive stable point marked and a table of candidate speeds.
- **How it works** — the four steps, the equations, and an explicit list of what the
  model assumes and where it stops.
- **Sources** — model details, method references, the open datasets for checking
  predictions, and where the constants come from.

## Renaming it

Change `SETTINGS["site_name"]` in `app.py` (or drop a `settings.json` next to it). The
header colours the last four letters, so `RajMill` renders as Raj + **Mill**, the same way
Raj3DLabs renders as Raj3D + **Labs**. `RajTurning` and `Chatterbox` work the same way.

## The models

**Stability.** Zero-order analytical solution (Altintas & Budak, CIRP Annals 44/1, 1995).
The directional coefficients are averaged over a tooth period, which turns the problem
into a quadratic eigenvalue problem solved in closed form at each chatter frequency:

    a₀Λ² + a₁Λ + 1 = 0,    a_lim = −2πΛ_R(1 + κ²)/(N·Kt),    κ = Λ_I/Λ_R
    ε = π − 2·arctan(κ),   T = (ε + 2kπ)/ω_c,   n = 60/(N·T)

Validated against the textbook result: for a 600 Hz mode and 4 teeth, the pockets land at
60·fn/(N·k) = 9000, 4500, 3000 rpm, and the predicted chatter frequency sits just above
the natural frequency.

**Roughness.** Geometric marks first — Ra = f²/(32r) for a nose radius, cusps fz²/(8R) for
a flat end mill wall, scallop h = R − √(R² − (ae/2)²) for ball-nose finishing — then
explicit correction factors for runout, minimum chip thickness and a process factor. Each
factor is displayed separately so you can see what the number is made of.

## What it does not model

Process damping (real low-speed cuts are more stable than this says), variable-pitch and
variable-helix cutters, the extra lobes that appear at very low radial immersion, spindle
speed variation, tool wear over the pass, and workpiece dynamics that change as material
comes off. For those, a semi-discretisation or time-domain simulation is the right tool.

The speed axis is also finite: below roughly 2,000 rpm for a typical mode the lobes are
packed closer than the speed grid resolves, so that band is greyed out rather than
plotted as if it meant something.

## Inputs worth getting right

Modal parameters (fn, ζ, k) and cutting force coefficients (Kt, Kr) dominate the answer.
The presets are representative values for classes of tool and material, not measurements
of your machine — tap-test your own setup, and calibrate Kt and Kr from cutting force
measurements, before trusting a figure to two decimal places.

## Layout

```
app.py                 entry point: page config + navigation
core/dynamics.py       FRF, directional coefficients, stability lobes
core/roughness.py      geometric roughness + correction factors
core/recommend.py      verdict assembly and computed actions
core/inputs.py         the sidebar form and cached solves
core/theme.py          palette, CSS, Plotly template
views/                 one script per page
demo_cases.py          ten verification cases, writes rajmill_test_cases.csv
tools/build_single_file.py   flattens everything into single_file/app.py
single_file/           app.py + requirements.txt, deployable on their own
.streamlit/config.toml light theme and colours
```

## Deploying

Streamlit Community Cloud, either way:

- **Single file (simplest).** Put `single_file/app.py`, `single_file/requirements.txt`
  and `.streamlit/config.toml` in the repo root and point Cloud at `app.py`.
- **Full project.** Push the whole folder, including `core/` and `views/`, and point Cloud
  at `app.py`. If those folders do not reach GitHub, `from core import theme` fails.

Keep `.streamlit/config.toml` in both cases: it fixes the light theme. Without it, a viewer
whose system is in dark mode gets a dark page under charts drawn for a white background.

After changing anything in `core/` or `views/`, run `python tools/build_single_file.py`
to regenerate the single file. There are no data files and no model weights, so the repo
stays tiny and the app starts cold in a couple of seconds.
