import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const envPath = path.resolve(__dirname, '..', '..', '..', '.env');
const requiredKeys = ['JIRA_URL', 'JIRA_EMAIL', 'JIRA_TOKEN', 'GROQ_KEY'];

loadChapterEnv();

export function getConfig() {
  const missing = requiredKeys.filter((key) => !process.env[key]?.trim());

  if (missing.length) {
    const error = new Error(`Missing required .env variables: ${missing.join(', ')}.`);
    error.status = 400;
    throw error;
  }

  return {
    jira: {
      baseUrl: normalizeJiraBaseUrl(process.env.JIRA_URL.trim()),
      email: process.env.JIRA_EMAIL.trim(),
      apiToken: process.env.JIRA_TOKEN.trim()
    },
    groq: {
      apiKey: process.env.GROQ_KEY.trim(),
      baseUrl: process.env.GROQ_BASE_URL?.trim() || 'https://api.groq.com/openai/v1',
      model: process.env.GROQ_MODEL?.trim() || 'openai/gpt-oss-120b'
    }
  };
}

export function getConfigStatus() {
  const variables = Object.fromEntries(
    requiredKeys.map((key) => [key, Boolean(process.env[key]?.trim())])
  );

  return {
    ready: Object.values(variables).every(Boolean),
    variables,
    jiraUrl: maskUrl(process.env.JIRA_URL),
    jiraEmail: maskEmail(process.env.JIRA_EMAIL),
    groqModel: process.env.GROQ_MODEL?.trim() || 'openai/gpt-oss-120b',
    groqBaseUrl: process.env.GROQ_BASE_URL?.trim() || 'https://api.groq.com/openai/v1'
  };
}

function maskUrl(value = '') {
  if (!value.trim()) return '';
  try {
    const url = new URL(value);
    return `${url.protocol}//${url.hostname}`;
  } catch {
    return 'configured';
  }
}

function maskEmail(value = '') {
  if (!value.trim()) return '';
  const [name, domain] = value.split('@');
  if (!domain) return 'configured';
  return `${name.slice(0, 2)}***@${domain}`;
}

function normalizeJiraBaseUrl(value) {
  try {
    return new URL(value).origin;
  } catch {
    return value.replace(/\/+$/, '');
  }
}

function loadChapterEnv() {
  let file = '';

  try {
    file = readFileSync(envPath, 'utf8');
  } catch {
    return;
  }

  for (const line of file.split(/\r?\n/)) {
    const match = line.match(/^\s*([^#=\s]+)\s*=\s*(.*)\s*$/);
    if (!match) continue;

    const [, key, rawValue] = match;
    process.env[key] = cleanEnvValue(rawValue);
  }
}

function cleanEnvValue(value) {
  const trimmed = value.trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}
