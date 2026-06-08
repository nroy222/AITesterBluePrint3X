import { safeReadText } from './safeReadText.js';

const jiraFields = [
  'summary',
  'description',
  'issuetype',
  'status',
  'priority',
  'assignee',
  'reporter',
  'labels',
  'components',
  'comment',
  'created',
  'updated'
].join(',');

export async function fetchJiraIssue(jira, jiraIssueId) {
  const baseUrl = jira.baseUrl.replace(/\/+$/, '');
  const endpoint = `${baseUrl}/rest/api/3/issue/${encodeURIComponent(jiraIssueId)}?fields=${jiraFields}&expand=names`;
  const auth = Buffer.from(`${jira.email}:${jira.apiToken}`).toString('base64');

  const response = await fetch(endpoint, {
    headers: {
      Authorization: `Basic ${auth}`,
      Accept: 'application/json'
    }
  });

  if (!response.ok) {
    const body = await safeReadText(response);
    const error = new Error(`Jira fetch failed (${response.status}): ${body || response.statusText}`);
    error.status = response.status;
    throw error;
  }

  const issue = await readJsonResponse(response, 'Jira');
  return normalizeJiraIssue(issue);
}

async function readJsonResponse(response, serviceName) {
  const body = await safeReadText(response);

  try {
    return JSON.parse(body);
  } catch {
    const error = new Error(`${serviceName} returned a non-JSON response. Check the base URL, credentials, and API permissions.`);
    error.status = 502;
    throw error;
  }
}

function normalizeJiraIssue(issue) {
  const fields = issue.fields || {};
  const comments = fields.comment?.comments || [];

  return {
    key: issue.key,
    summary: fields.summary || '',
    description: adfToText(fields.description),
    issueType: fields.issuetype?.name || '',
    status: fields.status?.name || '',
    priority: fields.priority?.name || '',
    assignee: fields.assignee?.displayName || 'Unassigned',
    reporter: fields.reporter?.displayName || '',
    labels: fields.labels || [],
    components: (fields.components || []).map((component) => component.name),
    comments: comments.map((comment) => ({
      author: comment.author?.displayName || '',
      created: comment.created || '',
      body: adfToText(comment.body)
    })),
    created: fields.created || '',
    updated: fields.updated || ''
  };
}

function adfToText(node) {
  if (!node) return '';
  if (typeof node === 'string') return node;
  if (Array.isArray(node)) return node.map(adfToText).filter(Boolean).join('\n');
  if (node.type === 'text') return node.text || '';
  if (node.type === 'hardBreak') return '\n';
  if (node.content) {
    const separator = ['paragraph', 'heading'].includes(node.type) ? '' : '\n';
    return node.content.map(adfToText).filter(Boolean).join(separator);
  }
  return '';
}
