# Project Constitution

## Project
Jira Test Plan Generator for `KAN-2`

## Data Schemas
Confirmed from the objective on 2026-06-08.

### Environment Configuration
```json
{
  "JIRA_URL": "https://example.atlassian.net",
  "JIRA_EMAIL": "qa@example.com",
  "JIRA_TOKEN": "jira-api-token",
  "GROQ_KEY": "groq-api-key",
  "GROQ_BASE_URL": "https://api.groq.com/openai/v1",
  "GROQ_MODEL": "openai/gpt-oss-120b"
}
```

### Generate Test Plan Request
```json
{
  "jiraIssueId": "KAN-2"
}
```

### Jira Issue Normalized Shape
```json
{
  "key": "KAN-2",
  "summary": "",
  "description": "",
  "issueType": "",
  "status": "",
  "priority": "",
  "assignee": "",
  "reporter": "",
  "acceptanceCriteria": "",
  "labels": [],
  "components": [],
  "comments": [],
  "created": "",
  "updated": ""
}
```

### Test Plan Output Payload
```json
{
  "test_plan": {
    "title": "",
    "source_issue": "KAN-2",
    "objective": "",
    "scope": {
      "in_scope": [],
      "out_of_scope": []
    },
    "assumptions": [],
    "risks": [],
    "test_scenarios": [
      {
        "id": "TP-001",
        "title": "",
        "priority": "High",
        "type": "Functional",
        "preconditions": [],
        "steps": [],
        "expected_result": "",
        "test_data": [],
        "automation_candidate": true
      }
    ],
    "traceability": [
      {
        "jira_field": "acceptanceCriteria",
        "covered_by": ["TP-001"]
      }
    ]
  }
}
```

## Behavioral Rules
- Fetch Jira issue `KAN-2` by default, while allowing another Jira issue key to be entered.
- Use Jira issue data as the source of truth.
- Generate a detailed manual QA test plan with positive, negative, edge, and regression coverage.
- Include assumptions when Jira data is incomplete.
- Do not silently invent requirements; mark inferred items as assumptions or risks.
- Load Jira and Groq credentials from `.env` on the server only. Do not commit real Jira or Groq secrets.
- Keep the frontend lightweight: it should show configuration readiness and ask only for the Jira issue key.

## Architectural Invariants
- Do not write scripts in `tools/` until discovery is answered, schema is confirmed, and the blueprint is approved.
- Keep business rules deterministic where possible.
- Use Jira data as the canonical source once the source-of-truth details are confirmed.
- Browser UI must call a local API proxy instead of sending Jira/Groq secrets directly from frontend code.
- Jira connection logic lives in `server/services/jiraConnection.js`.
- Test-plan generation logic lives in `server/services/testPlanCreator.js`.

## Maintenance Log
- 2026-06-08: Final local app uses `.env` for Jira/Groq config and `KAN-2` as the default issue.
- 2026-06-08: Final build, local API health, and React page checks passed. Live Jira/Groq generation is pending non-empty `.env` secrets.
