# Jira Test Plan Generator SOP

## Goal
Fetch a Jira issue, defaulting to `KAN-2`, and create a structured manual QA test plan from the issue data.

## Inputs
- `.env` values:
  - `JIRA_URL`
  - `JIRA_EMAIL`
  - `JIRA_TOKEN`
  - `GROQ_KEY`
- UI value:
  - `jiraIssueId`, defaulting to `KAN-2`

## Data Source
Jira is the source of truth. The app fetches the issue through Jira Cloud REST API v3.

## Logic
1. Load environment configuration from `chapter_03_BLAST_FW/.env`.
2. Validate that all required variables exist.
3. Fetch the Jira issue with Basic authentication.
4. Normalize Jira fields and Atlassian Document Format text into a smaller deterministic shape.
5. Ask Groq model `openai/gpt-oss-120b` to produce JSON only.
6. Parse and validate the JSON enough for UI rendering.
7. Render the test plan and allow Markdown copy/download.

## Edge Cases
- Missing `.env` variable: return a configuration error before any external API call.
- Jira issue not found or unauthorized: return Jira status and a concise error.
- Groq returns non-JSON text: extract the first JSON object if possible, otherwise fail clearly.
- Sparse Jira issue: place inferred or missing-detail items in assumptions or risks.

## Invariants
- Do not expose Jira token or Groq key to the frontend.
- Do not commit real secrets.
- Do not invent requirements as facts.
- Keep API calls in server-side modules.
