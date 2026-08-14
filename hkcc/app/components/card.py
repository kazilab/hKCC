"""Bordered card container that the hKCC theme can style.

``st.container(border=True)`` renders as an ordinary ``stVerticalBlock``: the
border is a styled-component prop, so nothing in the DOM tells a bordered
container apart from any other layout block. (Streamlit used to wrap it in a
``stVerticalBlockBorderWrapper`` test id, which is what the theme rules keyed on
until it was removed upstream — the rules then matched nothing and cards quietly
fell back to Streamlit's own surface colours.)

``key`` is the supported hook: Streamlit turns it into an ``st-key-<key>`` class
on the container element, so every card carries a key under one prefix and
:mod:`hkcc.app.theme` paints them all with a single attribute-substring rule.

Keys must be unique within a script run — hence the ``name`` argument. Inside a
loop, fold the loop index into it: the key exists only as a CSS hook, so an
index is preferable to a data-derived id, which would have to be trusted to be
unique before the page would render at all.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from streamlit.delta_generator import DeltaGenerator

CARD_KEY_PREFIX = "hkcc-card"


def card(name: str) -> DeltaGenerator:
    """A bordered container the theme styles. ``name`` must be unique per run."""
    return st.container(border=True, key=f"{CARD_KEY_PREFIX}-{name}")
