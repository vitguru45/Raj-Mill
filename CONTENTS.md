# What's in rajmill.zip

21 files, about 160 kB. No datasets and no model weights: everything is solved
from the equations at run time, so the whole app is roughly 1,300 lines of
Python and starts cold in a couple of seconds.

```
rajmill/
├── app.py                 entry point — SETTINGS block, branding, four tabs, visitor badge
├── demo_cases.py          the ten verification cases; run it live, writes a CSV
├── README.md              setup, equations used, what the model ignores, deployment
├── CONTENTS.md            this file
├── requirements.txt       five dependencies
├── .gitignore             keeps __pycache__, settings.json and the generated CSV out of git
├── core/
│   ├── dynamics.py        FRF, directional coefficients, stability lobes
│   ├── roughness.py       geometric Ra/Rz plus named correction factors
│   ├── recommend.py       verdict assembly and computed actions
│   ├── inputs.py          the shared sidebar form, material table, cached solve
│   ├── theme.py           SETTINGS header, Cambria stylesheet, Plotly template
│   └── __init__.py
├── views/
│   ├── predict.py         verdict, lobe diagram, roughness, actions, numbers
│   ├── process_map.py     speed × depth sweep and candidate speeds
│   ├── how_it_works.py    four steps, symbol table, equations, assumptions
│   ├── sources.py         model details, references, open datasets, constants
│   └── __init__.py
├── tools/
│   └── build_single_file.py   flattens core/ and views/ into single_file/app.py
├── single_file/
│   ├── app.py             the whole app in one file, generated, deploy on its own
│   └── requirements.txt   same five dependencies
└── .streamlit/config.toml theme colours (deploy this too)
```

`core/` holds the physics and imports Streamlit only in `theme.py` and
`inputs.py`, so `from core import dynamics` works in a notebook or a script.
`views/` holds widgets and no physics. Each view exposes one `render()`, which
`app.py` calls inside a tab.

## app.py

The `SETTINGS` dict at the top carries `site_name`, `tagline`, `lab_name`,
`credit`, the visitor-counter choice and the badge host, and a `settings.json`
beside it overrides any of them without touching code. The header colours the
last four letters of the name, so `RajMill` renders as Raj + **Mill**, the same
way Raj3DLabs renders as Raj3D + **Labs**; `RajTurning` and `Chatterbox` split
correctly too.

The sidebar form is built once and the stability solve runs once per settings
change, then all four tabs draw from the same result.

## core/dynamics.py

- `Mode`, `ToolDynamics` — modal description per direction; `Mode.frf` returns the
  receptance 1/(k(1 − r² + 2iζr)).
- `PRESETS`, `preset_dynamics` — five representative systems so the app works before a
  tap test, labelled as representative rather than measured.
- `engagement_angles` — entry and exit angles for up or down milling.
- `directional_coefficients` — the four averaged directional factors in closed form.
- `stability_lobes` — sweeps chatter frequency, solves both roots for every lobe number,
  and returns the scattered points plus a clean lower envelope. `_branch_on_grid`
  resamples each branch over the span it covers, which is what keeps the envelope from
  developing single-cell spikes.
- `n_reliable_min` — the speed below which lobes pack tighter than the grid resolves. It
  is also where process damping makes real cuts more stable than the model says, so both
  reasons agree: suggestions ignore that band and the plots grey it out.
- `stable_speed_suggestions` — contiguous stability pockets that clear the depth in use,
  each with its peak, its nearest usable speed and its width in rpm. Width matters: a
  90 rpm pocket is not usable on a real machine.

## core/roughness.py

Geometric value first — Ra = f²/(32r), Rz = f²/(8r) for a nose radius, cusps fz²/(8R) on
an end-milled wall, scallop height for ball-nose — then factors recorded by name: runout,
ploughing and the process factor. `effective_feed` opens the mark spacing toward feed per
revolution once one tooth's runout exceeds the feed per tooth. The minimum-chip-thickness
branch is the micro-milling case and is labelled a heuristic in the app. `feed_for_target_ra`
and `stepover_for_target_ra` invert the model, which is where the suggested feed comes from.

## core/recommend.py

Builds the verdict sentences (limit, depth, margin; expected Ra against target) and the
action list. Actions are derived: speeds from the pockets actually solved for, the depth
from 30% below the limit at the current speed, the lighter-immersion option by re-solving
the whole diagram at half the radial width to check it helps, the feed by inverting the
roughness model. When the condition is already good it reports the headroom instead.

## core/inputs.py

One sidebar shared by both working tabs so they cannot drift apart. Holds the material
table (Kt and Kr by material group, order-of-magnitude values), the `Setup` dataclass with
derived properties (feed rate, cutting speed, engagement angles), and the cached solve.

## views/

`predict.py` — verdict line, four metrics, two reasoning sentences, then inner tabs for
the lobe diagram, the roughness breakdown with an Ra-versus-feed curve, the recommended
changes, and the raw numbers with CSV export. Pocket markers are drawn only when the
current point fails.

`process_map.py` — speed against depth as a margin map, the most productive stable point
starred, and a table of candidate pocket speeds with the finish each would give.

`how_it_works.py` — the four steps, a full symbol table in an expander, the equations in
LaTeX, what the model assumes and where it stops.

`sources.py` — states up front that no ML model is used, then the model details, six
method references, six open datasets for checking predictions, where Kt, Kr and the modal
presets come from, the software list and the ownership caption.

## demo_cases.py

Ten cases built on the same functions the app calls: speed flip at constant depth, the two
lobe pockets, the immersion series, the stiffness pair, and the feed and runout pair for
finish. Prints the table and writes `rajmill_test_cases.csv`. Safe to run live.

## single_file/ and tools/

`tools/build_single_file.py` pastes every module into one `app.py` that imports
nothing local, for deployments where `core/` and `views/` do not reach GitHub.
Module docstrings become `#` comments in the output, because Streamlit "magic"
would otherwise print each one on the page. Edit the real modules and re-run it;
do not hand-edit the output.

## Checks run on this build

- `pyflakes` clean across every file.
- Every tab and inner tab opened, inputs changed mid-session (spindle speed, micro-tool
  toggle), no page errors and no server tracebacks.
- Changing tool dynamics (preset or own k, fn, ζ) re-solves the lobes; the cached solve
  is keyed on the modal numbers.
- Extreme sidebar values (10 and 200,000 rpm, 100 mm depth) keep the Process map inputs
  within their limits.
- Lobe speeds land at 60·fn/(N·k); chatter frequency sits just above fn; critical depth
  rises as immersion falls; Ra matches hand calculation and scales as f².

## Not in the zip

No virtual environment, no `__pycache__`, no `settings.json` (local override only), no
generated CSV, no authentication. Fine on localhost or a classroom link; put it behind a
login before it goes somewhere public.
