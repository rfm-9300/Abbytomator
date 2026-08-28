from __future__ import annotations

import pytest

from app.services.insights import MetaApiInsightsSource


def test_meta_api_stub_is_explicit() -> None:
    with pytest.raises(NotImplementedError, match="CSV"):
        MetaApiInsightsSource().fetch()
