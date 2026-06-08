import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { getConfig, getConfigStatus } from './services/config.js';
import { fetchJiraIssue } from './services/jiraConnection.js';
import { createTestPlan } from './services/testPlanCreator.js';

const app = express();
const port = Number(process.env.PORT || 3001);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distPath = path.resolve(__dirname, '..', 'dist');

app.use(express.json({ limit: '2mb' }));

app.get('/api/health', (_req, res) => {
  res.json({ ok: true });
});

app.get('/api/config-status', (_req, res) => {
  res.json(getConfigStatus());
});

app.post('/api/generate-test-plan', async (req, res) => {
  try {
    const jiraIssueId = String(req.body?.jiraIssueId || 'KAN-2').trim().toUpperCase();
    if (!jiraIssueId) {
      const error = new Error('Jira issue ID is required.');
      error.status = 400;
      throw error;
    }

    const config = getConfig();
    const issue = await fetchJiraIssue(config.jira, jiraIssueId);
    const testPlan = await createTestPlan(config.groq, issue);

    res.json({
      issue,
      testPlan
    });
  } catch (error) {
    res.status(error.status || 500).json({
      error: error.message || 'Unexpected error while generating the test plan.'
    });
  }
});

app.use(express.static(distPath));

app.use((_req, res) => {
  res.sendFile(path.join(distPath, 'index.html'));
});

app.listen(port, () => {
  console.log(`Jira Test Plan API listening on http://127.0.0.1:${port}`);
});
