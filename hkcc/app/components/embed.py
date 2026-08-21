"""Inline HTML rendering, replacing the removed ``st.components.v1.html``.

``components.v1.html`` rendered its markup into a sandboxed iframe. ``st.html``
inlines it into the page instead. Three differences follow from dropping the
iframe, and they are handled here once rather than at thirteen call sites:

**Height.** An iframe has to be told how tall to be. Inline content sizes itself,
so a bare ``height`` is not merely redundant - applying it would clip markup that
no longer has an iframe to scroll inside. Height is therefore honoured only when
the caller also asked for a scroll box.

**Scrolling.** ``scrolling=True`` gave the iframe its own scrollbars, which also
contained wide tables. Inline, that has to become an explicit ``max-height`` plus
``overflow:auto`` wrapper, or a long evidence matrix pushes the whole page
instead of scrolling within itself.

**JavaScript.** The iframe ran scripts; ``st.html`` strips them in the browser
unless told otherwise. Only the API page's copy button needs this, and it asks
for it explicitly - the default stays off.

The JavaScript opt-in is newer than this project's ``streamlit>=1.40`` floor, so
it is feature-detected rather than assumed. Raising the floor instead would mean
pinning a version number nothing else here needs.
"""

from __future__ import annotations

import inspect

import streamlit as st

#: ``st.html`` gained ``unsafe_allow_javascript`` well after 1.40. Passing it to
#: a build that predates it would raise TypeError on every call.
_HTML_ACCEPTS_JS = "unsafe_allow_javascript" in inspect.signature(st.html).parameters


def html_block(
    body: str,
    *,
    height: int | None = None,
    scrolling: bool = False,
    allow_javascript: bool = False,
) -> None:
    """Render an HTML string inline.

    Args:
        body: the markup. Inline ``style`` attributes and SVG survive intact;
            there are no ``<style>`` blocks in this app's builders, so nothing
            leaks into the surrounding page.
        height: maximum height in pixels. Applied only alongside ``scrolling``;
            see the module docstring.
        scrolling: give the block its own scroll box rather than letting it
            extend the page.
        allow_javascript: permit inline handlers. Off by default; the sandbox
            the iframe used to provide is gone, so scripts now run in the app's
            own document.
    """
    if scrolling and height:
        body = f'<div style="max-height:{height}px;overflow:auto">{body}</div>'
    if allow_javascript and _HTML_ACCEPTS_JS:
        st.html(body, unsafe_allow_javascript=True)
    else:
        st.html(body)
