Feature: Power BI visual containers
  As a Power BI report consumer
  I want automated checks that key visual containers are rendered

  Background:
    Given I open the base URL

  Scenario: Page loads
    Then the page title should contain "Microsoft Power BI"

  Scenario Outline: <chart> chart loads and scrolls horizontally
    Then the "<chart>" container should be visible
    And I scroll the container "<chart>" horizontally

    Examples:
      | chart                                                                   |
      | Weekly Trend of Late Audits and Audits Scheduled within next seven days |
      | Audit Delays Across Sites                                               |
      | Weekly Trend of Late Audits                                             |

  Scenario: table loads and scrolls vertically
    Then the "Audits Scheduled Within next 7 days" of column should be visible
    And I scroll the table of column "Audits Scheduled Within next 7 days" vertically
