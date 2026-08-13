"""HTML building blocks shared by the insight cards.

status_pill - solid-fill severity/classification label
id_chip     - outlined monospace chip for a copyable value (IP, CVE, port)
fingerprint - chip with the fingerprint segments coloured by position

Inline styles only; neutral text inherits the panel colour and uses opacity, so the
cards render on both the SecOps light and dark themes.
"""
from __future__ import annotations

import html

# severity/status: classification or level -> (fill, text-on-fill)
_STATUS = {
    "critical":    ("#B91C1C", "#FFFFFF"),
    "malicious":   ("#B91C1C", "#FFFFFF"),
    "high":        ("#D97706", "#1C1917"),
    "promiscuous": ("#D97706", "#1C1917"),
    "medium":      ("#F59E0B", "#1C1917"),
    "low":         ("#2563EB", "#FFFFFF"),
    "info":        ("#2563EB", "#FFFFFF"),
    "benign":      ("#15803D", "#FFFFFF"),
    "unknown":     ("#475569", "#FFFFFF"),
}
ACCENT = "#0073FF"            # ELLIO brand interactive (links, buttons)
GUIDE_LINE = "rgba(130,140,160,.45)"   # tree/footer rules; visible on light + dark
_BORDER = "#64748B"           # outline visible on light AND dark host surfaces
_SEP = "#94A3B8"              # fingerprint separators
# selection affordance: values select atomically (one click copies the whole value)
_SELECT_ALL = "-webkit-user-select:all;user-select:all;"
# categorical (field-identity) palette - assigned by POSITION, never by severity
_SLOT = ["#2563EB", "#059669", "#D97706", "#E11D48", "#7C3AED", "#4F46E5"]


def status_level(value: str) -> str:
    """Normalize a classification/severity value to a known status key.

    Args:
        value: The raw classification or severity string.

    Returns:
        A key of the status palette, or 'unknown' when unrecognized.
    """
    v = (value or "").lower()
    return v if v in _STATUS else "unknown"


def status_pill(label: str, level: str) -> str:
    """Solid-fill severity/classification pill; the label is uppercased.

    Args:
        label: The text shown on the pill.
        level: The status key that selects the fill colour.

    Returns:
        The pill HTML.
    """
    fill, fg = _STATUS[status_level(level)]
    return (f'<span style="display:inline-block;background:{fill};color:{fg};'
            f'border-radius:4px;padding:2px 8px;font-size:11px;font-weight:600;'
            f'margin:2px 4px 2px 0;">{html.escape(label.upper())}</span>')


def id_chip(text: str, border: str = "", text_color: str = "", mono: bool = True) -> str:
    """Outlined chip for a copyable value; one click selects the whole value.

    Args:
        text: The value shown in the chip.
        border: Optional outline colour; defaults to the neutral border.
        text_color: Optional text colour; defaults to the inherited panel colour.
        mono: Render the value in monospace.

    Returns:
        The chip HTML.
    """
    b = border or _BORDER
    tc = f"color:{text_color};" if text_color else ""   # else inherit panel colour
    font = "font-family:monospace;" if mono else ""
    # user-select:all -> one click selects the whole value atomically (easy copy/pivot)
    return (f'<span style="display:inline-block;border:1px solid {b};{tc}{font}'
            f'background:transparent;border-radius:4px;padding:1px 6px;font-size:11px;'
            f'margin:2px 4px 2px 0;white-space:nowrap;{_SELECT_ALL}">{html.escape(text)}</span>')


def _seg(text: str, slot: int) -> str:
    """Colour a fingerprint segment by its slot position.

    Args:
        text: The segment text.
        slot: The position that selects the categorical colour.

    Returns:
        The segment HTML.
    """
    return f'<span style="color:{_SLOT[slot % len(_SLOT)]};">{html.escape(text)}</span>'


def _sepc(ch: str) -> str:
    """Neutral-coloured separator character.

    Args:
        ch: The separator character.

    Returns:
        The separator HTML.
    """
    return f'<span style="color:{_SEP};">{html.escape(ch)}</span>'


def _fp_body(fmt: str, value: str) -> str:
    """Segment-coloured body for a MuonFP/JA4 fingerprint; other formats plain.

    Args:
        fmt: The fingerprint format name (e.g. MUONFP, JA4).
        value: The fingerprint value.

    Returns:
        The fingerprint body HTML.
    """
    f = fmt.upper()
    if f == "MUONFP":
        out = []
        for i, part in enumerate(value.split(":")):
            if i:
                out.append(_sepc(":"))
            out.append(_seg(part, i))
        return "".join(out)
    if f == "JA4":
        # Protocol(1) Version(2) SNIType(1) CipherCount(2) ExtCount(2) ALPN(2)
        #   _ CipherHash _ ExtHash ; colour the 10-char a-segment by position.
        parts = value.split("_")
        first = parts[0] if parts else value
        out = []
        if len(first) == 10:
            for slot, (a, b) in enumerate([(0, 1), (1, 3), (3, 4), (4, 6), (6, 8), (8, 10)]):
                out.append(_seg(first[a:b], slot))
        else:
            out.append(_seg(first, 0))
        for j, hp in enumerate(parts[1:]):
            out.append(_sepc("_"))
            out.append(_seg(hp, j))
        return "".join(out)
    return html.escape(value)   # unknown format -> plain monospace


def fingerprint(fmt: str, value: str) -> str:
    """Chip wrapping a segment-coloured monospace fingerprint; selects as one value.

    Args:
        fmt: The fingerprint format name (e.g. MUONFP, JA4).
        value: The fingerprint value.

    Returns:
        The fingerprint chip HTML.
    """
    return (f'<span style="display:inline-block;border:1px solid {_BORDER};'
            f'background:transparent;border-radius:4px;padding:1px 6px;font-size:11px;'
            f'margin:2px 4px 2px 0;white-space:nowrap;font-family:monospace;font-weight:bold;'
            f'vertical-align:middle;{_SELECT_ALL}">{_fp_body(fmt, value)}</span>')
