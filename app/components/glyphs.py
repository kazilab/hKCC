"""KCC glyph HTML for st.components.v1.html."""

from __future__ import annotations

import streamlit.components.v1 as components

from app import theme

GLYPH_PATHS = {
    "circle": '<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="1.5"/>',
    "helix": '<path d="M6 4c4 2 4 6 0 8s-4 6 0 8M18 4c-4 2-4 6 0 8s4 6 0 8" fill="none" stroke="currentColor" stroke-width="1.5"/>',
    "grid": '<path d="M4 4h16v16H4z M4 12h16 M12 4v16" fill="none" stroke="currentColor" stroke-width="1.2"/>',
    "marks": '<path d="M4 8h6M14 8h6M4 16h10" stroke="currentColor" stroke-width="1.5"/>',
    "rays": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4" stroke="currentColor" stroke-width="1.5"/>',
    "burst": '<circle cx="12" cy="12" r="3" fill="currentColor"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="currentColor"/>',
    "shield": '<path d="M12 3L4 7v5c0 5 3.5 8 8 9 4.5-1 8-4 8-9V7z" fill="none" stroke="currentColor" stroke-width="1.5"/>',
    "diamond": '<path d="M12 4l8 8-8 8-8-8z" fill="none" stroke="currentColor" stroke-width="1.5"/>',
    "loop": '<path d="M8 12a4 4 0 108 0" fill="none" stroke="currentColor" stroke-width="1.5"/>',
    "wave": '<path d="M4 14c2-4 4-4 6 0s4 4 6 0 4-4 6 0" fill="none" stroke="currentColor" stroke-width="1.5"/>',
    "dots": '<circle cx="8" cy="12" r="1.5" fill="currentColor"/><circle cx="12" cy="12" r="1.5"/><circle cx="16" cy="12" r="1.5"/>',
    "fade": '<path d="M6 16h12" stroke="currentColor" opacity=".3"/><path d="M8 12h8" opacity=".6"/><path d="M10 8h4" stroke="currentColor"/>',
    "tree": '<path d="M12 4v16M8 10h8M6 16h12" stroke="currentColor" stroke-width="1.5" fill="none"/>',
    "link": '<path d="M8 12h8M6 8h4v8H6zM14 8h4v8h-4z" stroke="currentColor" stroke-width="1.2" fill="none"/>',
}


def kcc_glyph_html(kind: str, *, size: int = 24, color: str | None = None) -> str:
    color = color or theme.THEME["accent"]
    inner = GLYPH_PATHS.get(kind, GLYPH_PATHS["circle"])
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 24 24" style="color:{color}">
      {inner}
    </svg>
    """


def render_glyph(kind: str, size: int = 24, color: str | None = None) -> None:
    components.html(kcc_glyph_html(kind, size=size, color=color), height=size + 8)
