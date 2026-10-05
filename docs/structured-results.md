# Structured Results

Pyxelator 1.0.0 preserves the established `bool`, coordinate-tuple, and `None`
returns of the legacy helpers. The structured API is additive: choose it when
an automation step needs evidence about *why* a match or action was accepted
or refused.

## Public imports

The supported import surface is the package root:

```python
from pyxelator import (
    ActionResult,
    MatchCandidate,
    MatchResult,
    Rectangle,
    VerificationResult,
    click_result,
    fill_result,
    match_result,
)
```

`Pyxelator(driver)` also exposes `click_result()` and `fill_result()` methods.

## Inspect a match before acting

`match_result()` accepts screenshot PNG/JPEG bytes and a template path. It
always returns a `MatchResult`; bad image data and unsafe matches are reported
as data rather than raised as matching exceptions.

```python
match_result(
    screenshot_bytes,
    template_path,
    confidence=0.7,
    grayscale=True,
    scales=None,
    ambiguity_margin=0.02,
)
```

```python
from pyxelator import match_result

screenshot = driver.get_screenshot_as_png()
result = match_result(
    screenshot,
    "templates/save.png",
    confidence=0.80,
    ambiguity_margin=0.02,
)

if result.ok:
    print("safe target", result.coordinates, result.score, result.scale)
else:
    print("refused", result.reason, result.score)
    for candidate in result.candidates:
        print(candidate.coordinates, candidate.score, candidate.scale)
```

`found` only means the winning score met the threshold. `ok` additionally
means no similarly scored, spatially distinct candidate made the target
ambiguous. Check `ok`, not `found`, before acting.

## Match result contract

| Type | Important fields |
|---|---|
| `Rectangle` | `x`, `y`, `width`, `height`, and computed `center` |
| `MatchCandidate` | `score`, `location`, `scale`, and computed `coordinates` |
| `MatchResult` | `ok`, `found`, `score`, `threshold`, `location`, `scale`, `ambiguous`, `screenshot_path`, `reason`, `candidates`, `score_margin`, and computed `coordinates` |
| `ActionResult` | `ok`, `action`, `match`, optional `verification`, `reason`, `artifacts`, and computed `failure` |
| `VerificationResult` | `ok`, `expected_visible`, `observed_visible`, `match`, and `reason` |

`MatchResult`, `ActionResult`, and `VerificationResult` are truthy only when
their `ok` field is true. The objects are frozen dataclasses, so evidence cannot
be silently changed after the action.

Stable matcher reasons include `below_threshold`, `ambiguous_match`,
`invalid_screenshot`, `invalid_template`, `flat_template`,
`template_too_large`, `no_usable_scale`, and `match_error`.

## Click with a safety gate and verification

The action APIs take one screenshot, reject a low-confidence or ambiguous
target, convert the accepted centre into driver coordinates, and only then
touch the page or device.

```python
click_result(
    driver,
    image,
    confidence=0.7,
    *,
    ambiguity_margin=0.02,
    verify_image=None,
    verification_confidence=None,
    verification_expected_visible=True,
    debug=False,
)
```

```python
from pyxelator import click_result

result = click_result(
    driver,
    "templates/save.png",
    confidence=0.80,
    verify_image="templates/saved-banner.png",
    verification_confidence=0.75,
    verification_expected_visible=True,
)

if not result:
    raise RuntimeError(
        f"save refused: {result.reason}; "
        f"score={result.match.score if result.match else None}"
    )

print("clicked at", result.match.coordinates)
print("post-action verification", result.verification.ok)
```

To prove that an image disappeared, set
`verification_expected_visible=False`. Disappearance passes only when a usable
post-action screenshot and template produced a below-threshold score. Invalid
inputs and matcher errors fail closed.

## Fill and keep the evidence

`fill_result()` accepts the same keyword-only safety and verification options
as `click_result()` after its required `text` argument.

```python
from pyxelator import fill_result

result = fill_result(
    driver,
    "templates/email-field.png",
    "user@example.com",
    confidence=0.80,
)

if result.ok:
    print("filled", result.match.location)
else:
    print("no text was written", result.reason)
```

`fill_result()` uses the coordinates from the accepted match. It does not call
legacy `fill()` and therefore does not rematch a potentially changed screen
before writing.

## Refusal is non-destructive

```python
result = click_result(driver, "templates/repeated-icon.png", confidence=0.75)

if result.reason == "ambiguous_match":
    # No click occurred. Use candidate evidence to improve the template.
    for candidate in result.match.candidates:
        print(candidate.location, candidate.score)
```

The same zero-action rule applies to `fill_result()` when screenshot capture,
matching, ambiguity checks, or coordinate validation fail.

Run `python examples/structured_results.py` for a deterministic offline flow
that exercises matching, click, fill, and ambiguity refusal without a browser
or network connection.
