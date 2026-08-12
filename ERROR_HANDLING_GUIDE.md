# Pyxelator Error Handling Guide

Every message Pyxelator prints, what causes it, and what to do about it.

All messages are prefixed `[Pyxelator]`. `ERROR` means the call returned `False`
or `None`; `WARNING` is informational and only appears with `verbose=True`.

**Start here:** most "it can't find my element" problems are answered by one call.

```python
from pyxelator import match_score

print(match_score(driver.get_screenshot_as_png(), 'button.png'))
```

| Score | Meaning |
|---|---|
| `0.9` - `1.0` | Solid match. If `find()` still fails, the threshold is too high. |
| `0.7` - `0.9` | Match. This is the normal range for a real element. |
| `0.5` - `0.7` | Weak. The element is probably there but looks different, or the template includes too much surrounding layout. |
| below `0.4` | The element is not on screen. Recapturing the template will not help. |
| `None` | The template cannot be matched at all - solid colour, bigger than the screen, or not a readable image. |

---

## 1. Template image file not found

```
[Pyxelator ERROR] Template image file not found: 'button.png'
```

With `debug=True` you also get the working directory:

```
[Pyxelator] Current working directory: /home/you/project
[Pyxelator] Tip: Use absolute path or ensure the file exists in current directory
```

**Cause.** The path does not exist. Usually the test runs from a different
directory than you expect - paths are resolved relative to the working
directory, not to the test file.

**Fix.** Build the path from the test file's own location:

```python
from pathlib import Path

TEMPLATES = Path(__file__).parent / 'templates'
click(driver, str(TEMPLATES / 'button.png'))
```

---

## 2. Element not found

```
[Pyxelator ERROR] Element not found after 3 attempts: 'button.png'
[Pyxelator] Best match scored 0.42, below the 0.70 threshold.
[Pyxelator] That is a weak, partial match. Likely causes:
[Pyxelator]   - the template includes surrounding layout, not just the element
[Pyxelator]   - the element is styled differently now (hover, disabled, theme)
```

The second line is the useful one: it reports the score the template actually
reached. The advice after it changes based on that score, so read it rather than
reaching for `confidence=0.5` by reflex.

### "That is close. Try confidence=0.68."

The element is there, rendered slightly differently - antialiasing, a subtly
different shade, a scrollbar shifting the layout. Use the suggested value.

### "That is a weak, partial match."

Part of the template matches and part does not. Almost always the template
includes more than the element: padding, a neighbouring label, background that
has since changed.

Recapture it cropped tightly to the element itself.

### "The element is almost certainly not on screen."

The score is too low for this to be a template problem. Check in this order:

```python
# 1. Has it finished rendering?
from selenium.webdriver.support.ui import WebDriverWait
WebDriverWait(driver, 10).until(lambda d: d.execute_script(
    "return document.readyState") == "complete")

# 2. Is it scrolled into view? Pyxelator matches the visible viewport only.
driver.execute_script("window.scrollTo(0, 400)")

# 3. Is something covering it - a cookie banner, a modal, a toast?
```

### "The closest match was at 0.8x the template's size."

The template was captured at a different window size. Sizes from 0.66x to 1.54x
are handled automatically, so seeing this means the difference is at the edge of
that range or beyond. Recapture at the size the test actually runs at.

### "The template could not be matched at all."

```
[Pyxelator] The template could not be matched at all. Usually one of:
[Pyxelator]   - it is a solid block of one colour, with no detail to match on
[Pyxelator]   - it is larger than the screenshot at every size tried
[Pyxelator]   - the file is not a readable image
```

A single-colour template is rejected deliberately: with no variation in it, the
maths behind matching reports a perfect score at every position on the page, so
it would "match" anywhere. Capture something with an edge, an icon or text in it.

### "The template (1920x893) is larger than the screenshot (1280x720)."

```
[Pyxelator] It looks like a screenshot of the whole page rather than of one
[Pyxelator] element. Crop it down to just the button or field.
```

Exactly what it says.

---

## 3. Element is not clickable

```
[Pyxelator ERROR] Element is not clickable
[Pyxelator] Found: <DIV> "Some text content..."
[Pyxelator] This is not a clickable element (button, link, etc).
[Pyxelator] Your template may be matching the wrong area of the page.
[Pyxelator] Tip: Recapture a smaller screenshot focused on the actual button.
```

The template matched, but whatever sits at those coordinates is not clickable.
Pyxelator checks for a `<button>`, `<a>`, `[onclick]`, `[role="button"]` or
`cursor: pointer` ancestor before clicking, and refuses rather than clicking
into a container.

The `Found:` line tells you what it hit. `<DIV>`, `<MAIN>` or `<HTML>` means the
template is matching layout rather than the control - usually because it
includes whitespace around the button, so the centre lands outside it.

Recapture cropped to the button's visible edges.

---

## 4. Element is not fillable

```
[Pyxelator ERROR] Element is not fillable
[Pyxelator] Found: <BUTTON> "Submit"
[Pyxelator] This is not a fillable element (input, textarea, etc).
```

`fill()` needs an `<input>`, `<textarea>` or `[contenteditable]`. The `Found:`
line shows what matched instead. Two common cases:

- **The template caught the label, not the field.** Labels sit next to inputs and
  look distinctive, so they are easy to crop by accident. Capture the input box.
- **The field is empty and featureless.** An empty input is close to a solid
  rectangle, which makes a poor template. Include its border and any placeholder
  text, or the icon beside it.

---

## 5. Appium messages

```
[Pyxelator ERROR] Tap at (540, 1200) failed: WebDriverException: ...
[Pyxelator] Gestures use the W3C Actions protocol, which needs an Appium 2.0+ server
```

Gestures need an Appium 2.0+ server. The older `TouchAction` protocol is not
used - it was removed from Appium-Python-Client in 3.0.

```
[Pyxelator ERROR] Could not type into the focused element: ...
[Pyxelator] The tap landed at (540, 1200) but no text field took focus.
```

The tap worked but nothing became editable. Usually the template matched a label
rather than the input, or the keyboard had not appeared yet.

```
[Pyxelator ERROR] Invalid swipe direction: 'sideways'
[Pyxelator] Expected one of: up, down, left, right
```

```
[Pyxelator ERROR] Swipe would not move: already at the screen edge
```

The element is at the edge and cannot be swiped further that way. Swipes are
clamped to the screen because drivers reject out-of-bounds coordinates; when
clamping leaves nowhere to go, the swipe is refused rather than performed as a
gesture that does nothing.

---

## Debug mode

```python
click(driver, 'button.png', debug=True)
fill(driver, 'input.png', 'text', debug=True)
swipe_app(driver, 'item.png', 'up', debug=True)
```

Adds the working directory on a missing file, per-attempt progress, the
coordinates found, and which click method succeeded.

`find()` and `locate()` use `verbose=True` instead - they return a value rather
than acting, so they stay quiet by default:

```python
locate(driver, 'button.png', verbose=True)
```

---

## Troubleshooting workflow

```python
from pathlib import Path
from pyxelator import match_score, locate, click

template = str(Path(__file__).parent / 'templates' / 'button.png')

# 1. Does the file exist?
assert Path(template).exists(), template

# 2. How close is it? This answers most questions on its own.
score = match_score(driver.get_screenshot_as_png(), template)
print(f"score: {score}")

# 3. Where does it think the element is?
print(locate(driver, template, verbose=True))

# 4. What happens on a click?
click(driver, template, debug=True)
```

If step 2 gives a good score but step 4 reports "not clickable", the template is
matching the right area but its centre is landing off the control - crop tighter.

---

## Retries

`click()` retries 3 times with a 0.5s gap by default, which covers an element
still animating in. It does not wait for navigation - use your framework's own
wait for that.

```python
click(driver, 'button.png', retries=5, delay=1.0)
```

Note that each retry takes a fresh screenshot and repeats the match, and a
failing match searches every size in the scale ladder. A `click()` that is going
to fail therefore takes a few seconds to say so.

---

## Message summary

| Message | Meaning | First thing to try |
|---|---|---|
| `Template image file not found` | Bad path | Build the path from `__file__` |
| `Best match scored X, below Y` | Matched too weakly | Read the advice that follows it |
| `could not be matched at all` | Unusable template | Not solid colour; smaller than the screen |
| `larger than the screenshot` | Whole-page template | Crop to one element |
| `Element is not clickable` | Hit a container | Crop to the button's edges |
| `Element is not fillable` | Hit a label or button | Capture the input box |
| `Tap at (x, y) failed` | Appium gesture rejected | Use an Appium 2.0+ server |
| `no text field took focus` | Tapped a non-input | Capture the input, not its label |
| `Swipe would not move` | Element at the edge | Swipe the other way, or shorter |
