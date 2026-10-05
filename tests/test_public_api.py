"""Public import-surface checks for the additive structured API."""

import pyxelator
from pyxelator import actions, core, results


def test_structured_api_is_exported_from_package_root():
    expected = {
        "match_result": core.match_result,
        "click_result": actions.click_result,
        "fill_result": actions.fill_result,
        "Rectangle": results.Rectangle,
        "MatchCandidate": results.MatchCandidate,
        "MatchResult": results.MatchResult,
        "ActionResult": results.ActionResult,
        "VerificationResult": results.VerificationResult,
    }

    for name, value in expected.items():
        assert name in pyxelator.__all__
        assert getattr(pyxelator, name) is value


def test_structured_modules_define_intentional_public_surfaces():
    assert actions.__all__ == ["click_result", "fill_result"]
    assert results.__all__ == [
        "Rectangle",
        "MatchCandidate",
        "MatchResult",
        "VerificationResult",
        "ActionResult",
    ]


def test_v1_release_version():
    assert pyxelator.__version__ == "1.0.0"
