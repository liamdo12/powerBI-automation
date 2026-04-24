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

## Issues?
1. The Power BI report page can't capture correctly
=> The issue was the whole page was embedded as an iframe, it can't be used like normal approach to capture the elements

2. How to find the XPATH of the element?
=> I have to setup debugging mode by using the `context.page.pause()` with the `--no-capture` flag from the Behave then use the debug tool to find correct path. 
For some of the complicated XPATH like the relative path `ancestor-or-self::visual-container`, I have to enable the developer tool in browser, look up and try for each of the components, their parents and capture the classes.

3. Why there are JS code?
=> Pure Playwright API can't be worked correctly when scrolling. So I have to use an alternative approach by capturing the scroll bar (`svg` element) then use it to scroll left, right, up, down

4. Why there are multiple level of capturing the label?
=> I tried to use a single `get_by_label` for all the labels but it doesn't work correctly, it failed to capture the label several times. Some of the label was a column header so it needs to handle differently.
I came up with a solution to use multiple strategies to get the label, so it can guarantee that the script will always find the correct data (first correct strategy returns)

5. Playwright API and Behave for Gherkins definition
=> I need to get familiar with the Playwright API by checking their documentation, try their functions, test with the PowerBI to see if they work. I also need to explore the Behave documentation for the integration.

## Improvements
1. The current automation tool only works with the exact PowerBI site that defined in the config since it detects the scrollable containers by label
=> Improve to automatically detect the scrollable containers without label and can work with different PowerBI sites



