# Power BI Automation tool

## Problem statement

Power BI dashboards often contain multiple tables with their own internal vertical and horizontal scrollbars. 
A simple screenshot only captures what's visible, missing rows and columns hidden behind the scroll. Build a Python automation tool that captures the full content of such tables. Use any website page with scrollable tables to build this project

## Solution
A simple automation tool that using the Playwright API with Behave and JavaScript that will visit a PowerBI site and find all the scrollable containers by label to capture them.

## Project structure

```
  PowerBI_Automation/
  ├── README
  ├── behave.ini
  ├── requirements.txt
  │
  ├── constants/
  │   ├── power_bi.py
  │   └── urls.py
  │
  ├── features/
  │   ├── environment.py
  │   │
  │   ├── check_containers.feature
  │   └── steps/
  │       └── web_steps.py
  │
  ├── pages/
  │   ├── base_page.py
  │   └── report_page.py
  │
  ├── utils/
  │   └── image_stitch.py
  │
  └── reports/
      └── output/
```

## Flows
1. The script will load the Power BI page and verify it exists
2. It will check each of the charts, tables to see if they were available.
3. For each of the chart, it will calculate the bounding (x, y) and determines the steps to scroll
4. Before scrolling, it will reset all the states of the chart (e.g: scroll back to left most)
5. After each scrolling step, it will capture the image and store them as list of bytes then transform and merge into a single image

## Technical stack
- Python 3.13.7
- Playwright 1.58.0
- Behave 1.3.3
- Pillow >=10

## Setup

Requires Python 3.13+. From the project root:

```bash

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate


pip install -r requirements.txt

playwright install chromium
```

## How to run

Default run (headless Chromium against the URL in `constants/urls.py`):

```bash
behave
```

Common overrides via Behave's `-D key=value` userdata (these keys are read in `features/environment.py` and `behave.ini`):

| Key              | Default   | Purpose                                     |
|------------------|-----------|---------------------------------------------|
| `headless`       | `true`    | set `false` to watch the browser            |
| `browser`        | `chromium`| `chromium` / `firefox` / `webkit`           |
| `base_url`       | Power BI  | point at a different report                 |
| `viewport_width` | `1280`    | viewport size                               |
| `viewport_height`| `720`     |                                             |
| `visual_timeout` | `30000`   | ms to wait for a visual to render           |

Examples:

```bash

behave -D headless=false


behave -D visual_timeout=45000


behave -n "Weekly trend chart loads"


behave features/check_containers.feature
```

### Outputs

- `reports/output/`       — stitched scroll-capture panoramas (PNG)
- `reports/junit/`        — JUnit XML, one file per scenario
- `reports/screenshots/`  — screenshot for any step that failed or errored

## Issues & resolutions

### 1. The Power BI report page couldn't be captured correctly
The page is embedded inside an `iframe`, so ordinary top-level element lookups return nothing. Resolved by resolving the hosting frame first (`_frame()` in `ReportPage`) and running all queries against that frame.

### 2. How to find the XPath of an element?
Enabled Behave's debug mode with `context.page.pause()` + the `--no-capture` flag, then used the browser devtools to inspect the actual DOM. For relative paths like `ancestor-or-self::visual-container`, I walked the parent chain in devtools and picked the innermost stable class.

### 3. Why is there JS in the page object?
The pure Playwright API couldn't drive Power BI's custom SVG scrollbars and cross-element DOM queries in one round-trip. The remaining JS (in `constants/power_bi.py`) is read-only inspection — locating the visual's bbox, finding the SVG track/thumb rects, reading native `scrollTop`. The actual scroll itself is pure Playwright (`page.mouse.wheel`).

### 4. Why multiple strategies for finding a label?
A single `get_by_label` failed intermittently — Power BI renders titles as split headings, aria-labelled wrappers, `title` attributes, or SVG text depending on the visual type. Column headers live in a different subtree altogether. `container_by_title` runs strategies in priority order (heading → aria-label → title attr → visible text); the first visible hit wins.

### 5. Getting familiar with Playwright + Behave
Combined the Playwright Python docs with small Power BI experiments to map its APIs onto the report's DOM, and the Behave docs to wire steps + `environment.py` hooks correctly.

## Improvements
1. The current automation tool only works with the exact PowerBI site that defined in the config since it detects the scrollable containers by label
=> Improve to automatically detect the scrollable containers without label and can work with different PowerBI sites



