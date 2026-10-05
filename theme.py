"""Shared look and feel: page config, CSS and the Plotly template.

Everything visual lives here so the pages stay about signals, not styling.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

APP_NAME = "RajMill"          # rename the app here
CONTACT = "you@example.com"

INK = "#15233a"
INK_2 = "#5a6b7e"
GRID = "#e2e8ec"
SIGNAL = "#2451d6"
DETAIL = "#d98e04"
GOOD = "#1f7a4d"
BAD = "#b3261e"
BAND_COLORS = ["#2451d6", "#d98e04", "#b3651c", "#6b7a3a", "#3f8f8a", "#7a4fa3",
               "#a33a5b", "#8a5a00"]

_template = go.layout.Template()
_template.layout = go.Layout(
    font=dict(family="Archivo, Helvetica Neue, Arial, sans-serif", color=INK, size=13),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=60, r=20, t=30, b=45),
    xaxis=dict(gridcolor=GRID, zerolinecolor="#cbd5dd", linecolor="#cbd5dd"),
    yaxis=dict(gridcolor=GRID, zerolinecolor="#cbd5dd", linecolor="#cbd5dd"),
    legend=dict(orientation="h", y=1.12, x=0),
    colorway=BAND_COLORS,
)
pio.templates["signalbench"] = _template
pio.templates.default = "signalbench"

CSS = """
<style>
  /* Cambria everywhere, matching the Raj3DLabs house style (falls back to Georgia
     / Times on Mac, Android and Linux). Icons and code keep their own fonts. */
  .stApp *:not([data-testid="stIconMaterial"]):not(code):not(pre):not(pre *) {
      font-family: Cambria, "Cambria Math", Georgia, "Times New Roman", serif !important;}
  .block-container {padding-top: 3.2rem; max-width: 1180px;}
  .rm-brand {font-size: 2.4rem; font-weight: 700; line-height: 1.3; margin: 0; padding-top: 4px;}
  .rm-brand span {color: #E4572E;}
  .rm-sub {color: #8B4513; margin-top: -4px; font-size: 1.02rem;}
  .rm-credit {color: #4169E1; font-size: 1.0rem; margin: 2px 0 6px;}
  .rm-verdict {font-size: 1.6rem; font-weight: 700; line-height: 1.25; margin: 2px 0 10px;}
  .ok {background:#dcfce7; color:#166534;} .warn {background:#fef3c7; color:#92400e;} .bad {background:#fee2e2; color:#991b1b;}
  .step-num {font-size: 2rem; font-weight: 700; color: #4169E1; line-height: 1;}
  .rule {border-top: 2px solid #15233a; margin: 0.4rem 0 1rem;}
  div[data-testid="stMetricValue"] {font-weight: 700;}
</style>
"""


def setup(site_name: str = APP_NAME) -> None:
    """Page config and CSS. Called once, from app.py."""
    st.set_page_config(page_title=site_name, layout="wide",
                       initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)


def header(settings: dict) -> None:
    """Brand block: name with the last four letters in accent, tagline, credit."""
    brand = settings["site_name"]
    st.markdown(f"<div class='rm-brand'>{brand[:-4]}<span>{brand[-4:]}</span></div>",
                unsafe_allow_html=True)
    st.markdown(f"<div class='rm-sub'>{settings['tagline']} &middot; {settings['lab_name']}</div>",
                unsafe_allow_html=True)
    if settings.get("credit"):
        st.markdown(f"<div class='rm-credit'>{settings['credit']}</div>",
                    unsafe_allow_html=True)


def caption_row(pairs: list[tuple[str, str]]) -> None:
    """A single line of 'label value' pairs, like the summary bar on the pages."""
    st.markdown(
        " &nbsp;&nbsp;&nbsp; ".join(
            f"<span style='color:{INK_2}'>{k}</span> <b>{v}</b>" for k, v in pairs),
        unsafe_allow_html=True)
