# Jira Test Plan Generator

Lightweight React app for fetching a Jira issue, defaulting to `KAN-2`, and generating a QA test plan with Groq.

## Run
```bash
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## `.env`
The app reads configuration from:

```text
../.env
```

Required values:

```text
JIRA_URL=
JIRA_EMAIL=
JIRA_TOKEN=
GROQ_KEY=
```

Optional values:

```text
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=openai/gpt-oss-120b
```

The browser never receives Jira or Groq secrets. It only calls the local API with the Jira issue ID.
