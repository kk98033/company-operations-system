"""Reduce an untrusted User-Agent to a short non-identifying label."""

from __future__ import annotations


def summarize_user_agent(user_agent: str | None) -> str:
    """Return broad browser/platform names without versions or raw header text."""

    value = user_agent or ""
    browser = (
        "Edge"
        if "Edg/" in value
        else "Firefox"
        if "Firefox/" in value
        else "Chrome"
        if "Chrome/" in value or "CriOS/" in value
        else "Safari"
        if "Safari/" in value
        else "瀏覽器"
    )
    platform = (
        "Windows"
        if "Windows" in value
        else "Android"
        if "Android" in value
        else "iPhone／iPad"
        if "iPhone" in value or "iPad" in value
        else "macOS"
        if "Macintosh" in value
        else "Linux"
        if "Linux" in value
        else "未知裝置"
    )
    return f"{browser}／{platform}"
