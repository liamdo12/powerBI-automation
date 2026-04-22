Feature: Power BI visual containers
  As a Power BI report consumer
  I want automated checks that key visual containers are rendered
  So that regressions on the published report are caught early

  Background:
    Given I open the base URL

  Scenario: Page loads
    Then the page title should contain "Microsoft Power BI"

  Scenario: Weekly trend container renders
    Then the "Weekly Trend of Late Audits and Audits Scheduled within next seven days" container should be visible
    Then I scroll the container "Weekly Trend of Late Audits and Audits Scheduled within next seven days" horizontally
#    Then the "Audit Delays Across Sites" container should be visible
#    Then the "Weekly Trend of Late Audits" container should be visible
#    Then the "Audits Scheduled Within next 7 days" of column should be visible


