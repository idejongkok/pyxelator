# Pyxelator - Project Structure

```
locateonapps/
│
├── pyxelator.py
├── README.md
├── .gitignore
├── STRUCTURE.md
│
├── test_pyxelator_selenium.py
├── test_pyxelator_playwright.py
│
└── templates/
    ├── masuk.png
    ├── poster.png
    └── editbutton.png
```

## Main Files

### Core Library
- **pyxelator.py** - Main library with simple API

### Documentation
- **README.md** - Complete usage guide and API reference
- **STRUCTURE.md** - Project structure (this file)

### Tests
- **test_pyxelator_selenium.py** - Selenium integration tests
- **test_pyxelator_playwright.py** - Playwright integration tests

### Template Images
- **templates/** - Folder containing example template images for testing
  - **masuk.png** - Login button template
  - **poster.png** - Example element template
  - **editbutton.png** - Edit button template

## Usage

### Install Dependencies
```bash
pip install opencv-python numpy selenium playwright
```

### Run Tests
```bash
# Selenium tests
pytest test_pyxelator_selenium.py -v

# Playwright tests
pytest test_pyxelator_playwright.py -v

# All tests
pytest -v
```

### Quick Example
```python
from pyxelator import find, click, fill
from selenium import webdriver

driver = webdriver.Chrome()
driver.get('https://example.com')

if find(driver, 'button.png'):
    click(driver, 'button.png')
```

## API Overview

### Simple Function API
```python
from pyxelator import find, click, fill

# Check if element exists
if find(driver, 'button.png'):
    print("Found!")

# Click element
click(driver, 'submit.png')

# Fill text
fill(driver, 'email.png', 'user@example.com')
```

### Class-based API
```python
from pyxelator import Pyxelator

px = Pyxelator(driver)
px.find('button.png')
px.click('button.png')
px.fill('input.png', 'text')
```

## Contributing

See README.md for contribution guidelines.
