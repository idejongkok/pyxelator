"""Structured, framework-neutral result types for incremental v1 APIs.

The legacy helpers still return ``bool``, coordinate tuples, or ``None``. These
objects provide an additive result contract that new matching and action APIs
can adopt without changing those established return values.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

__all__ = [
    "Rectangle",
    "MatchCandidate",
    "MatchResult",
    "VerificationResult",
    "ActionResult",
]


@dataclass(frozen=True)
class Rectangle:
    """A rectangle in screenshot pixels."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        """Return the rectangle's centre in screenshot pixels."""
        return self.x + self.width // 2, self.y + self.height // 2


@dataclass(frozen=True)
class MatchCandidate:
    """One spatially distinct template-matching candidate."""

    score: float
    location: Rectangle
    scale: float

    @property
    def coordinates(self) -> Tuple[int, int]:
        """Return the candidate centre in screenshot pixels."""
        return self.location.center


@dataclass(frozen=True)
class MatchResult:
    """Evidence produced by one template-matching attempt.

    ``found`` means the best candidate met ``threshold``. ``ok`` additionally
    requires that no similarly scored, spatially distinct candidate made the
    target ambiguous. Callers must check ``ok`` before acting on its location.

    A rejected candidate may still provide ``score``, ``location``, ``scale``,
    and ranked ``candidates`` for diagnostics.
    """

    ok: bool
    found: bool
    score: Optional[float]
    threshold: float
    location: Optional[Rectangle]
    scale: Optional[float]
    ambiguous: bool = False
    screenshot_path: Optional[str] = None
    reason: Optional[str] = None
    candidates: Tuple[MatchCandidate, ...] = ()
    score_margin: Optional[float] = None

    def __bool__(self) -> bool:
        """Allow natural truth checks while keeping the evidence accessible."""
        return self.ok

    @property
    def coordinates(self) -> Optional[Tuple[int, int]]:
        """Return the candidate centre, if a candidate was measurable."""
        if self.location is not None:
            return self.location.center
        return None


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of an optional post-action visual verification."""

    ok: bool
    expected_visible: bool
    observed_visible: bool
    match: Optional[MatchResult] = None
    reason: Optional[str] = None

    def __bool__(self) -> bool:
        return self.ok


@dataclass(frozen=True)
class ActionResult:
    """Framework-neutral outcome for action APIs to adopt incrementally."""

    ok: bool
    action: str
    match: Optional[MatchResult] = None
    verification: Optional[VerificationResult] = None
    reason: Optional[str] = None
    artifacts: Tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return self.ok

    @property
    def failure(self) -> Optional[str]:
        """Compatibility-friendly name used by the proposed explicit API."""
        return None if self.ok else self.reason
