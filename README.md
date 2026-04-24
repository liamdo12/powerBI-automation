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



