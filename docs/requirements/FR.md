Functional requirements describe what the system should actually do the features and behaviours a user can see and use.

| ID | Requirement |
| :--- | :--- |
| FR1 | User can add (register) an API endpoint by giving its URL, the status code it should return, and how often it should be checked. |
| FR2 | System keeps checking each saved endpoint again and again using a background job queue (BullMQ). After every check it schedules the next one. |
| FR3 | System can tell when an endpoint has failed - this includes timeout, wrong status code, connection error, or bad SSL certificate. |
| FR4 | System calculates uptime percentage for each endpoint and gives it through a reporting API. |
| FR5 | System does not create an incident on the very first failure. It waits and only creates an incident once failures cross a set limit (like 3 in a row). |
| FR6 | System sends only one alert per change of state (healthy to failing), not one alert per failed check, so the user does not get spammed. |
| FR7 | System sends incident alerts through Slack, Discord, Email or a webhook, whichever the user has set up. |
| FR8 | If sending a notification fails, system tries again up to 3 times with growing wait time between tries, then marks it failed and logs it. |
| FR9 | System stores old uptime and response-time data so it can be looked up later. Recent data should be fast to fetch, older data can be a bit slower. |
| FR10 | System shows a dashboard where a team lead can see, at one glance, how all their endpoints are doing and which ones have an open incident. |
| FR11 | New user gets a simple onboarding flow to sign up and add their first endpoint quickly. |
| FR12 | When checking someone else's API, system should not hit it too often, should back off if it keeps failing, and should identify itself properly in the request. |
| FR13 | User can set up and manage their notification details (Slack webhook link, email address, etc.) for their account or for a single endpoint. |
| FR14 | System can generate a monthly uptime report per user, which can be downloaded or fetched through the API. |
| FR15 | User can set a maintenance window for an endpoint (a planned time range) during which checks still happen but no alert/incident is raised, so planned deployments do not trigger false alarms. |
| FR16 | Response Body & JSONPath Assertions: Users can set rules to check specific text strings, regex patterns, or JSONPath values inside the response body. |
| FR17 | Verify Payload Data & Response Body Assertions. |
| FR18 | Role-Based Access Control (RBAC): Admins can grant granular permissions (e.g., Admin, Operator, Read-Only) to team members. |
| FR19 | Multi-Region Probe Selection: Allowing users to pick geographic origin regions (e.g., US-East, EU-Central, AP-South) to detect localized network routing issues. |
