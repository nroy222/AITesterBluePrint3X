# Findings

## Objective
- Build a Test Plan Generator that fetches data for Jira issue `KAN-2`.

## Known Constraints
- BLAST Protocol 0 requires discovery, schema definition, and blueprint approval before any scripts are written in `tools/`.
- JSON input/output payload shapes must be confirmed in `gemini.md` before coding begins.
- The app should avoid exposing Jira and Groq credentials in bundled browser code.

## Open Findings
- The user's real Jira base URL, Jira email, Jira token, and Groq API key will be entered in the app settings at runtime.

## Research
- Jira Cloud REST API supports fetching an issue by key through `/rest/api/3/issue/{issueIdOrKey}`.
- Groq exposes an OpenAI-compatible API with `https://api.groq.com/openai/v1` as the base URL and chat completions at `/chat/completions`.
- Current `.env` variables available: `GROQ_KEY`, `JIRA_EMAIL`, `JIRA_TOKEN`, `JIRA_URL`.
- Required `.env` keys are present but currently empty, so the app correctly reports configuration as not ready.
- After values were added, Node's built-in env loader still did not expose them, so the server now uses a small deterministic parser scoped to the chapter `.env`.
- A deep Jira UI URL can produce HTML instead of JSON when `/rest/api/3` is appended after its path. The server now normalizes `JIRA_URL` to the URL origin.
- GitHub/research scan did not identify a repo pattern worth copying for this small app. The final design uses direct Jira REST calls and a focused native QA prompt.
