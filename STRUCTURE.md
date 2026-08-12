# Pyxelator - Project Structure

For contributors. If you just want to use the library, see [README.md](README.md).

```
pyxelator/
│
├── pyxelator/                  the package
│   ├── __init__.py             public API + driver dispatch
│   ├── core.py                 template matching (OpenCV only)
│   ├── utils.py                driver detection, coordinate conversion, diagnostics
│   └── adapters/
│       ├── __init__.py
│       ├── selenium.py         Selenium WebDriver
│       ├── playwright.py       Playwright
│       └── appium.py           Appium (beta)
│
├── tests/                      unit tests - no browser, no device
│   ├── test_core.py            matching, thresholds, malformed input
│   ├── test_multiscale.py      the scale ladder and its limits
│   ├── test_utils.py           coordinate conversion, driver detection
│   ├── test_explain_miss.py    failure diagnosis
│   └── test_appium_adapter.py  W3C gestures, via a fake driver
│
├── README.md                   usage and API reference
├── ERROR_HANDLING_GUIDE.md     what each error message means
├── STRUCTURE.md                this file
├── DEPLOY.md                   release process
│
├── pyproject.toml              packaging + pytest config
├── setup.py                    kept for older tooling; pyproject is the source of truth
├── requirements.txt
└── LICENSE
```

## How the layers fit together

```
your test
    │
    │  find / locate / click / fill  (same call for every framework)
    ▼
__init__.py ─── detect_driver_type() ──▶ picks an adapter
    │
    ▼
adapters/{selenium,playwright,appium}.py
    │   take the screenshot
    │   convert coordinates into the driver's space
    │   perform the click / fill / tap
    ▼
core.py
        match the template against the screenshot
```

**The split that matters:** `core.py` knows nothing about browsers or drivers -
it takes screenshot bytes and a template path and returns coordinates. That is
why the whole matching layer is testable without launching anything, and why
adding a framework means writing one adapter rather than touching the matching
code.

### `core.py`

Pure OpenCV. Public entry points:

| Function | Returns |
|---|---|
| `find_image_in_screenshot()` | `(x, y)` or `None` |
| `locate_match()` | `Match` (adds score, screenshot size, scale) or `None` |
| `match_score()` | best score regardless of threshold |
| `check_image_exists()` | `bool` |
| `image_sizes()` | screenshot and template dimensions, for diagnostics |

Coordinates are in **screenshot pixels**. Converting them is the adapter's job.

### `utils.py`

| Function | Purpose |
|---|---|
| `detect_driver_type()` | Selenium / Playwright / Appium, from the driver's module |
| `to_css_pixels()` | screenshot pixels → the driver's coordinate space |
| `explain_miss()` | why a template did not match, in words |

### `adapters/`

Each adapter provides `find`, `locate`, `click` and `fill`; Appium adds
`swipe_app`. Names are suffixed per framework (`find_pw`, `find_app`) so the
dispatcher in `__init__.py` can import them all side by side.

Framework packages are imported **inside** the functions that need them, never
at module level, so `import pyxelator` works with only OpenCV installed.

## Running the tests

```bash
pip install -e ".[dev]"
pytest
```

`pyproject.toml` sets `testpaths = ["tests"]`, so a bare `pytest` collects only
the unit tests. They need no browser and finish in seconds.

Any `test_*.py` at the repo root is a personal scratch script that drives a real
browser against a live site - those are gitignored and are not part of the suite.

## Adding support for another framework

1. Add `pyxelator/adapters/<name>.py` with `find`, `locate`, `click`, `fill`.
   Import the framework's own package inside the functions, not at module level.
2. Take the screenshot, call `core.locate_match()`, then convert the coordinates
   with `utils.to_css_pixels()` - skipping that step breaks every HiDPI display.
3. Teach `utils.detect_driver_type()` to recognise the driver.
4. Add a branch to each dispatcher in `pyxelator/__init__.py`.
5. Add tests with a fake driver. See `tests/test_appium_adapter.py` - it asserts
   real gesture payloads without an emulator.
