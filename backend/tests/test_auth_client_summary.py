"""Safe coarse labels for untrusted browser User-Agent headers."""

import pytest

from app.modules.auth.client_summary import summarize_user_agent


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("Mozilla/5.0 (Windows NT 10.0) Edg/140.0", "Edge／Windows"),
        ("Mozilla/5.0 (Macintosh) Firefox/142.0", "Firefox／macOS"),
        ("Mozilla/5.0 (iPhone) Version/18 Safari/605.1", "Safari／iPhone／iPad"),
        (None, "瀏覽器／未知裝置"),
    ],
)
def test_summary_uses_broad_names_without_versions(raw_value: str | None, expected: str) -> None:
    result = summarize_user_agent(raw_value)

    assert result == expected
    assert "140.0" not in result
    assert "142.0" not in result
