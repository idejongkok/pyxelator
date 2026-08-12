# Pyxelator

![PYXELATOR](https://bucket.idejongkok.my.id/pyxelator/PYXELATOR.png)

**Pixel-based Element Locator for Web & Mobile Automation**

Visual element automation for Selenium, Playwright & Appium. No more XPath hunting - just use screenshots!

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Why Pyxelator?

Traditional web automation requires finding elements by:
- XPath (breaks easily)
- CSS Selectors (tedious to write)
- IDs/Classes (may not exist)

**With Pyxelator, you just need screenshots!**
- Take screenshot of button/field
- Use it to find & interact
- Works with ANY element

---

## Installation

```bash
pip install pyxelator
```

**Optional Framework Dependencies:**
```bash
# For Selenium
pip install pyxelator[selenium]

# For Playwright
pip install pyxelator[playwright]

# For Appium (Beta)
pip install pyxelator[appium]

# For all frameworks
pip install pyxelator[dev]
```

---

## Quick Start

### **Super Simple API**

```python
from pyxelator import find, click, fill
from selenium import webdriver

driver = webdriver.Chrome()
driver.get('https://example.com')

# That's it! Just use images!
if find(driver, 'login_button.png'):
 click(driver, 'login_button.png')
 fill(driver, 'email_field.png', 'user@example.com')
```

### **Or use OOP style**

```python
from pyxelator import Pyxelator
from selenium import webdriver

driver = webdriver.Chrome()
driver.get('https://example.com')

px = Pyxelator(driver)

if px.find('login_button.png'):
 px.click('login_button.png')
 px.fill('email_field.png', 'user@example.com')
```

---

## API Reference

### Module Functions (Recommended)

#### `find(driver, image, confidence=0.7)`
Check if element exists.

```python
if find(driver, 'button.png'):
 print("Button found!")
```

**Parameters:**
- `driver` - Selenium WebDriver or Playwright Page
- `image` - Path to template image
- `confidence` - Match confidence 0.0-1.0 (default: 0.7)

**Returns:** `True` if found, `False` otherwise

---

#### `locate(driver, image, confidence=0.7)`
Get element coordinates.

```python
coords = locate(driver, 'button.png')
if coords:
 print(f"Button at {coords}") # (x, y)
```

**Returns:** `(x, y)` tuple or `None`

---

#### `click(driver, image, confidence=0.7, retries=3, delay=0.5, debug=False)`
Click element by image.

```python
click(driver, 'submit_button.png')
click(driver, 'button.png', retries=5, delay=1.0, debug=True)
```

**Parameters:**
- `driver` - Selenium WebDriver, Playwright Page, or Appium driver
- `image` - Path to template image
- `confidence` - Match confidence 0.0-1.0 (default: 0.7)
- `retries` - Number of retry attempts (default: 3, Selenium/Playwright only)
- `delay` - Delay between retries in seconds (default: 0.5, Selenium/Playwright only)
- `debug` - Print debug information (default: False)

**Returns:** `True` if clicked, `False` if not found

---

#### `fill(driver, image, text, confidence=0.7, debug=False)`
Fill text into element.

```python
fill(driver, 'email_field.png', 'user@example.com')
fill(driver, 'password.png', 'secret123', debug=True)
```

**Parameters:**
- `driver` - Selenium WebDriver, Playwright Page, or Appium driver
- `image` - Path to template image
- `text` - Text to fill into the element
- `confidence` - Match confidence 0.0-1.0 (default: 0.7)
- `debug` - Print debug information (default: False)

**Returns:** `True` if filled, `False` if not found

---

### Class API

#### `Pyxelator(driver)`

```python
from pyxelator import Pyxelator

px = Pyxelator(driver)
px.find('button.png')
px.click('button.png')
px.fill('input.png', 'text')
```

**Methods:**
- `find(image, confidence=0.7)` bool
- `locate(image, confidence=0.7)` tuple or None
- `click(image, confidence=0.7)` bool
- `fill(image, text, confidence=0.7)` bool

---

## Usage Examples

### Selenium

```python
from selenium import webdriver
from pyxelator import find, click, fill
import time

driver = webdriver.Chrome()
driver.get('https://example.com')
time.sleep(1)

# Login flow
if find(driver, 'login_button.png'):
 fill(driver, 'username.png', 'myuser')
 fill(driver, 'password.png', 'mypass')
 click(driver, 'submit.png')
 print("Logged in!")

driver.quit()
```

### Playwright

```python
from playwright.sync_api import sync_playwright
from pyxelator import find, click, fill
import time

with sync_playwright() as p:
 browser = p.chromium.launch(headless=False)
 page = browser.new_page()
 page.goto('https://example.com')
 time.sleep(1)

 # Same API!
 if find(page, 'login_button.png'):
 fill(page, 'username.png', 'myuser')
 fill(page, 'password.png', 'mypass')
 click(page, 'submit.png')
 print("Logged in!")

 browser.close()
```

### Appium (Beta - Mobile Automation)

```python
from appium import webdriver
from appium.options.android.uiautomator2.base import UiAutomator2Options
from pyxelator import find, click, fill
import time

# Setup Appium
options = UiAutomator2Options()
options.udid = "your_device_id"
options.platform_name = "Android"
options.app_package = "com.example.app"
options.app_activity = "com.example.app.MainActivity"

driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
time.sleep(2)

# Same API works for mobile!
if find(driver, 'login_button.png'):
 fill(driver, 'email_field.png', 'user@example.com')
 fill(driver, 'password_field.png', 'password123')
 click(driver, 'submit_button.png')
 print("Logged in!")

driver.quit()
```

#### Swiping (Appium only)

```python
from pyxelator import swipe_app

# Swipe up 300px starting from the centre of the matched element
swipe_app(driver, 'list_item.png', 'up', 300)

# Slower drag - some apps ignore a fast flick
swipe_app(driver, 'slider_handle.png', 'right', 200, duration=0.6)
```

**Parameters:**
- `driver` - Appium driver
- `image` - Path to template image (the swipe starts at its centre)
- `direction` - `'up'`, `'down'`, `'left'` or `'right'`
- `distance` - Distance in pixels (default: 200)
- `confidence` - Match confidence 0.0-1.0 (default: 0.7)
- `duration` - Seconds spent travelling (default: 0.2). Raise it if the app treats the gesture as a fling.
- `debug` - Print debug information (default: False)

**Returns:** `True` if swiped, `False` if the element was not found, the direction is invalid, or the gesture failed

A swipe that would run past the screen edge is clamped to it. If clamping leaves
nowhere to move, the swipe is refused rather than performed as a no-op.

> **Note:** Appium support is currently in **Beta**. Template matching works best with unique UI elements. For optimal results, use high-confidence templates and ensure elements are fully visible on screen.
>
> Gestures use the W3C Actions protocol and need an **Appium 2.0+ server**.

### Pytest Integration

```python
import pytest
from selenium import webdriver
from pyxelator import find, click, fill
import time

@pytest.fixture
def driver():
 driver = webdriver.Chrome()
 driver.maximize_window()
 yield driver
 driver.quit()

def test_login(driver):
 driver.get('https://example.com')
 time.sleep(1)

 assert find(driver, 'login_button.png') == True
 assert click(driver, 'login_button.png') == True
 assert fill(driver, 'email.png', 'test@example.com') == True
```

---

## Creating Template Images

### Best Practices:

1. **Screenshot ONE element** (button, field, icon)
2. **Keep it small** (50x50 to 300x200 pixels)
3. **Choose unique elements** (avoid generic ones)
4. **Crop tightly** around the element
5. **Use descriptive names** (`login_button.png`, `email_field.png`)

### How to Create:

```python
# Helper script to create templates
from selenium import webdriver
import time

driver = webdriver.Chrome()
driver.get('https://yoursite.com')
time.sleep(2)

# Take full screenshot
driver.save_screenshot('fullpage.png')

# Now open fullpage.png in image editor
# Crop the specific element you want
# Save as: login_button.png, email_field.png, etc.
```

---

## Confidence Levels

Adjust `confidence` parameter for matching accuracy:

```python
# Strict matching (0.8-1.0)
find(driver, 'button.png', confidence=0.9)

# Balanced (0.7) - RECOMMENDED
find(driver, 'button.png', confidence=0.7)

# Relaxed (0.5-0.6)
find(driver, 'button.png', confidence=0.5)
```

**Recommendation:** Start with `0.7`, adjust if needed.

### Window size and multi-scale matching

Template matching is very sensitive to size. A template captured at one window
size scores near zero against the same page rendered even 4% wider - which is
why "recapture at the same window size" used to be the standard advice.

Pyxelator now tries the template at a ladder of sizes automatically, so a
template captured on one window generally still works on another:

| Template vs page | Result |
|---|---|
| 0.66x - 1.54x | Found, no configuration needed |
| exactly 0.5x / 2.0x | Found - covers a display with a different device pixel ratio |
| below 0.66x, above 1.54x | Not found - recapture the template |

Two narrow bands (around 1.06x and 1.55x) score just under the 0.7 default;
`confidence=0.65` covers them.

**Cost.** A template that matches at its captured size short-circuits, so the
common case is unaffected - measured at 112ms with the ladder vs 127ms without,
on a 1920x893 screenshot. A template that matches at *no* size pays for the
whole ladder: ~1.0s instead of ~113ms. That only affects the not-found path, but
it is worth knowing if you call `find()` in a loop as a presence check.

To match only at the captured size:

```python
from pyxelator import find_image_in_screenshot

find_image_in_screenshot(shot, 'button.png', scales=(1.0,))

# Or globally, before your tests run:
import pyxelator.core
pyxelator.core.DEFAULT_SCALES = (1.0,)
```

**Limitation.** The winning size is whichever ladder rung scores highest. When
the real element sits between two rungs *and* a similar-looking element sits
exactly on one, the look-alike can win. Templates cropped tightly around
something visually distinctive avoid this.

### Picking a value with `match_score()`

Instead of guessing, ask how close the template actually came:

```python
from pyxelator import match_score

score = match_score(driver.get_screenshot_as_png(), 'button.png')
print(score)
# 0.62  -> element is there but rendering differs slightly; try confidence=0.6
# 0.13  -> element is not on screen; the template is wrong or the page changed
# None  -> template unreadable, larger than the screen, or a solid colour
```

A score is a `TM_CCOEFF_NORMED` correlation from -1.0 to 1.0. Anything at or
above your `confidence` counts as a match.

---

## Framework Compatibility

**Selenium WebDriver** - Fully supported
**Playwright** - Fully supported
**Appium** - Beta (mobile & desktop apps)

Pyxelator automatically detects which framework you're using!

### Appium Beta Status

Appium support is functional but still in beta. Known considerations:
- Works with native mobile apps (Android/iOS)
- Uses W3C Actions API for tap gestures
- Template matching may require lower confidence (0.5-0.6) for some elements
- Best results with high-resolution screenshots and unique UI elements

---

## Error Handling & Debugging

### Debug Mode (v0.4.0+)

Enable detailed logging to troubleshoot issues:

```python
# Click with debug mode
click(driver, 'button.png', debug=True)

# Fill with debug mode
fill(driver, 'input.png', 'text', debug=True)
```

**Debug output shows:**
- File existence validation
- Element search attempts
- Coordinates found
- Clickability/fillability validation
- Success/failure details

### Common Errors & Solutions

#### File Not Found
```
[Pyxelator ERROR] Template image file not found: 'button.png'
```
**Solution:** Check file path, use absolute path, or verify file exists

#### Element Not Found
```
[Pyxelator ERROR] Element not found after 3 attempts: 'button.png'
[Pyxelator] Best match scored 0.42, below the 0.70 threshold.
[Pyxelator] That is a weak, partial match. Likely causes:
[Pyxelator]   - the template includes surrounding layout, not just the element
[Pyxelator]   - the element is styled differently now (hover, disabled, theme)
```
**Solution:** Read the score and the advice under it - both change depending on
how close the match was, so the right fix differs. A score below 0.4 means the
element is not on screen and no template change will help. See
[ERROR_HANDLING_GUIDE.md](ERROR_HANDLING_GUIDE.md) for each case.

#### Element Not Clickable
```
[Pyxelator ERROR] Element is not clickable
[Pyxelator] Found: <DIV> "Some text..."
```
**Solution:** Recapture a smaller screenshot focused on the actual button

#### Element Not Fillable
```
[Pyxelator ERROR] Element is not fillable
[Pyxelator] Found: <BUTTON> "Submit"
```
**Solution:** Ensure template captures an input/textarea field, not a button

### Retry Mechanism

Configure retry attempts for flaky elements:

```python
# Retry up to 5 times with 1 second delay
click(driver, 'button.png', retries=5, delay=1.0)
```

---

## Troubleshooting

### Element Not Found?

1. **Check the score first** - `match_score(driver.get_screenshot_as_png(), 'button.png')`.
   This answers most cases on its own: above 0.7 the element is there, below 0.4 it is not.
2. **Read the failure message** - it reports the score and tailors its advice to it
3. **Verify element visibility** - matching only sees the visible viewport, so scroll to it first
4. **Check nothing is covering it** - cookie banners and modals are the usual culprits
5. **Crop the template tighter** - just the element, no surrounding layout
6. **Check template size** - must be smaller than the viewport

### Click Not Working?

1. **Enable debug mode** to see what's happening
2. **Verify element is clickable** (Pyxelator now validates this automatically)
3. **Add retry attempts** - `click(driver, 'button.png', retries=5)`
4. **Check if element is covered** by other elements

### Fill Not Working?

1. **Enable debug mode** for detailed error info
2. **Ensure element is input field** (Pyxelator validates this)
3. **Try clicking before filling** to focus the element
4. **Recapture template** focused on input field, not label

---

## Advanced Usage

### Multiple Actions

```python
from pyxelator import Pyxelator

px = Pyxelator(driver)

# Chain actions
if px.find('login.png'):
 px.fill('email.png', 'user@test.com')
 px.fill('pass.png', '12345')
 px.click('submit.png')
```

### Custom Confidence Per Element

```python
# Strict for critical buttons
click(driver, 'delete_button.png', confidence=0.9)

# Relaxed for dynamic elements
fill(driver, 'search_box.png', 'query', confidence=0.6)
```

### Error Handling

```python
if not find(driver, 'button.png'):
 print("Button not found, taking alternative action...")
 # Fallback logic here
```

---

## Testing

Run tests:

```bash
# Selenium tests
pytest test_pyxelator_selenium.py -v

# Playwright tests
pytest test_pyxelator_playwright.py -v

# All tests
pytest -v
```

---

## Contributors

**Author & Maintainer:**
- Aria Uno Suseno ([@idejongkok](https://instagram.com/idejongkok))

**Contributors:**
- Eri Permadi
- Yali Yanto Silitonga

**Testers:**
- Eri Permadi
- Yali Yanto Silitonga

---

## Contributing

Contributions welcome! Please:

1. Contact me first on Instagram @idejongkok
2. Fork the repository
3. Create feature branch
4. Add tests
5. Submit pull request

---

## License

MIT License - see LICENSE file

---

## Changelog

### v0.5.0

- **FIX:** Coordinates are now scaled from screenshot pixels to CSS pixels, so
  `click()` and `fill()` hit the element on HiDPI displays instead of missing by
  the device pixel ratio. Also fixes Appium on iOS, where taps use points.
- **FIX:** `click()` no longer fires every handler twice. It dispatched a
  synthetic `click` event *and* called native `.click()`, double-submitting forms.
- **FIX:** Removed the `TM_CCORR_NORMED` fallback. It does not subtract the mean,
  so it scored 0.93-0.99 on almost any pair of images and returned confident
  coordinates for elements that were not on screen.
- **FIX:** Reject solid-colour templates. `TM_CCOEFF_NORMED` is `0/0` for these
  and OpenCV resolves it to 1.0 everywhere, so they matched at (0, 0) on anything.
- **FIX:** `swipe_app()` works again. It was built on `TouchAction`, removed in
  Appium-Python-Client 3.0, so it returned `False` on every supported client.
  Rewritten on W3C Actions, along with the dead fallbacks in `click_app()`/`fill_app()`.
- **FIX:** `from pyxelator import swipe_app` works. Its docstring documented that
  import but the function was never exported.
- **FIX:** Appium failures report the cause instead of a bare `False`.
- **FIX:** Return `None` instead of crashing on an undecodable screenshot.
- **NEW:** Multi-scale matching. A template captured at one window size now
  matches from 0.66x to 1.54x, plus exact 0.5x/2.0x for a device pixel ratio
  change. Previously a 4% difference was enough to fail. Matches at the captured
  size short-circuit, so successful lookups cost nothing extra.
- **NEW:** `match_score()` reports how close a template came, for picking a
  `confidence` value.
- **NEW:** Failure messages report the actual score and tailor their advice to it.
- **NEW:** `Match.scale` reports which size a template matched at.
- **NEW:** `swipe_app()` takes `duration` and `debug`, validates its direction,
  and clamps the gesture to the screen.
- **NEW:** `grayscale=False` genuinely matches on colour. It previously converted
  the template to grayscale anyway, making the flag a no-op.
- **NEW:** Unit test suite (`tests/`) - 141 tests, no browser or device needed.
- **DOCS:** `ERROR_HANDLING_GUIDE.md` rewritten and actually shipped; it was
  referenced but never committed.
- **DOCS:** `STRUCTURE.md` rewritten - it described the old single-file layout.

> **Upgrade notes**
>
> `locate()` returns CSS pixels now, not raw screenshot pixels. Identical on a
> standard-DPI display. Remove any HiDPI offset workaround of your own.
>
> Elements that only ever matched through the old CCORR fallback will now report
> as not found, which is correct - they were never really being matched. Run
> `match_score()` on anything that stops being located.

### v0.4.0
- **NEW:** Comprehensive error handling for all adapters (Selenium, Playwright, Appium)
- **NEW:** File validation - checks if template image exists before processing
- **NEW:** Clickability detection - validates element is clickable before clicking (Selenium & Playwright)
- **NEW:** Fillability detection - validates element is fillable before filling text (Selenium & Playwright)
- **NEW:** Debug mode - detailed logging with `debug=True` parameter for troubleshooting
- **NEW:** Retry mechanism - configurable retry attempts for Selenium & Playwright (default: 3 retries)
- **NEW:** React compatibility - proper event handling for React form inputs
- **IMPROVED:** Clear, actionable error messages with troubleshooting tips
- **IMPROVED:** Smart element detection - finds clickable/fillable parent elements
- **DOCS:** Complete error handling guide (ERROR_HANDLING_GUIDE.md)
- **DOCS:** Updated implementation status for all adapters

### v0.3.1
- **Beta:** Appium support for mobile automation
- W3C Actions API integration for mobile gestures
- Enhanced template matching algorithm
- Bug fixes and stability improvements

### v0.2.x
- Playwright support improvements
- Enhanced error handling

### v0.1.0 (Initial Release)
- Selenium support
- Playwright support
- Auto framework detection
- Simple function API
- OOP class API
- Template matching with OpenCV
- Click, fill, find, locate actions

---

## Support

- Issues: [GitHub Issues](https://github.com/idejongkok/pyxelator/issues)
- Docs: [Full Documentation](https://pyxelator.pages.dev)
- Discussions: [GitHub Discussions](https://github.com/idejongkok/pyxelator/discussions)

---
more question find me on:

- Instagram: [https://instagram.com/idejongkok](https://instagram.com/idejongkok)
- YouTube: [https://youtube.com/idejongkok](https://youtube.com/idejongkok)
- Website: [https://idejongkok.com](https://idejongkok.com)

**Happy Automating! from idejongkok with love**
