import {
  CheckCircle2,
  Clipboard,
  Download,
  LoaderCircle,
  Play,
  RefreshCw,
  ServerCog,
  TriangleAlert
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

export default function App() {
  const [jiraIssueId, setJiraIssueId] = useState('KAN-2');
  const [configStatus, setConfigStatus] = useState(null);
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [copyState, setCopyState] = useState('idle');

  const markdown = useMemo(() => (result ? testPlanToMarkdown(result.testPlan, result.issue) : ''), [result]);

  useEffect(() => {
    refreshConfigStatus();
  }, []);

  async function refreshConfigStatus() {
    setIsLoadingConfig(true);
    setError('');

    try {
      const response = await fetch('/api/config-status');
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Unable to read configuration status.');
      setConfigStatus(data);
    } catch (statusError) {
      setError(statusError.message);
    } finally {
      setIsLoadingConfig(false);
    }
  }

  async function generateTestPlan(event) {
    event.preventDefault();
    setIsGenerating(true);
    setError('');
    setResult(null);
    setCopyState('idle');

    try {
      const response = await fetch('/api/generate-test-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jiraIssueId })
      });
      const data = await response.json();

      if (!response.ok) throw new Error(data.error || 'Failed to generate the test plan.');

      setResult(data);
    } catch (generationError) {
      setError(generationError.message);
    } finally {
      setIsGenerating(false);
    }
  }

  async function copyMarkdown() {
    await navigator.clipboard.writeText(markdown);
    setCopyState('copied');
    window.setTimeout(() => setCopyState('idle'), 1400);
  }

  function downloadMarkdown() {
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${jiraIssueId.trim() || 'jira'}-test-plan.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const ready = Boolean(configStatus?.ready);

  return (
    <main className="app-shell">
      <section className="workspace">
        <form className="control-panel" onSubmit={generateTestPlan}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">BLAST Final</p>
              <h1>Jira Test Plan Generator</h1>
            </div>
            <ServerCog aria-hidden="true" />
          </div>

          <ConfigCard status={configStatus} loading={isLoadingConfig} onRefresh={refreshConfigStatus} />

          <fieldset>
            <legend>Issue</legend>
            <label>
              Jira ID
              <input
                type="text"
                value={jiraIssueId}
                onChange={(event) => setJiraIssueId(event.target.value.toUpperCase())}
                required
              />
            </label>
          </fieldset>

          <button className="primary-action" type="submit" disabled={isGenerating || isLoadingConfig || !ready}>
            {isGenerating ? <LoaderCircle className="spin" aria-hidden="true" /> : <Play aria-hidden="true" />}
            {isGenerating ? 'Generating' : 'Create Test Plan'}
          </button>
        </form>

        <section className="output-panel" aria-live="polite">
          {error ? (
            <div className="notice error">
              <TriangleAlert aria-hidden="true" />
              <p>{error}</p>
            </div>
          ) : null}

          {!result && !error ? (
            <div className="empty-state">
              <CheckCircle2 aria-hidden="true" />
              <h2>{ready ? 'Ready for KAN-2' : 'Waiting for .env'}</h2>
              <p>
                {ready
                  ? 'Generate a structured QA test plan from the Jira issue.'
                  : 'Add the required Jira and Groq values to the chapter .env file.'}
              </p>
            </div>
          ) : null}

          {result ? (
            <>
              <div className="result-header">
                <div>
                  <p className="eyebrow">{result.issue.key}</p>
                  <h2>{result.testPlan.test_plan?.title || 'Generated Test Plan'}</h2>
                </div>
                <div className="result-actions">
                  <button type="button" onClick={copyMarkdown} title="Copy Markdown">
                    <Clipboard aria-hidden="true" />
                    {copyState === 'copied' ? 'Copied' : 'Copy'}
                  </button>
                  <button type="button" onClick={downloadMarkdown} title="Download Markdown">
                    <Download aria-hidden="true" />
                    Download
                  </button>
                </div>
              </div>

              <IssueSnapshot issue={result.issue} />
              <TestPlanView plan={result.testPlan.test_plan} />
            </>
          ) : null}
        </section>
      </section>
    </main>
  );
}

function ConfigCard({ status, loading, onRefresh }) {
  const variables = status?.variables || {};

  return (
    <section className={status?.ready ? 'config-card ready' : 'config-card'}>
      <div className="config-topline">
        <div>
          <h2>Environment</h2>
          <p>{loading ? 'Checking configuration' : status?.ready ? 'Configured from .env' : 'Missing required values'}</p>
        </div>
        <button type="button" onClick={onRefresh} title="Refresh configuration">
          <RefreshCw aria-hidden="true" />
        </button>
      </div>

      <div className="config-grid">
        {['JIRA_URL', 'JIRA_EMAIL', 'JIRA_TOKEN', 'GROQ_KEY'].map((key) => (
          <span className={variables[key] ? 'status-pill ok' : 'status-pill missing'} key={key}>
            {key}
          </span>
        ))}
      </div>

      {status?.ready ? (
        <dl className="config-meta">
          <div>
            <dt>Jira</dt>
            <dd>{status.jiraUrl}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{status.jiraEmail}</dd>
          </div>
          <div>
            <dt>Groq</dt>
            <dd>{status.groqModel}</dd>
          </div>
        </dl>
      ) : null}
    </section>
  );
}

function IssueSnapshot({ issue }) {
  return (
    <section className="issue-snapshot">
      <h3>Jira Issue Snapshot</h3>
      <dl>
        <div>
          <dt>Summary</dt>
          <dd>{issue.summary}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{issue.status || 'Unknown'}</dd>
        </div>
        <div>
          <dt>Priority</dt>
          <dd>{issue.priority || 'Unspecified'}</dd>
        </div>
        <div>
          <dt>Assignee</dt>
          <dd>{issue.assignee}</dd>
        </div>
      </dl>
    </section>
  );
}

function TestPlanView({ plan }) {
  if (!plan) return null;

  return (
    <article className="test-plan">
      <section>
        <h3>Objective</h3>
        <p>{plan.objective}</p>
      </section>

      <section className="two-column">
        <ListBlock title="In Scope" items={plan.scope?.in_scope} />
        <ListBlock title="Out of Scope" items={plan.scope?.out_of_scope} />
      </section>

      <section className="two-column">
        <ListBlock title="Assumptions" items={plan.assumptions} />
        <ListBlock title="Risks" items={plan.risks} />
      </section>

      <section>
        <h3>Test Scenarios</h3>
        <div className="scenario-list">
          {(plan.test_scenarios || []).map((scenario) => (
            <div className="scenario-card" key={scenario.id}>
              <div className="scenario-topline">
                <span>{scenario.id}</span>
                <strong>{scenario.title}</strong>
                <small>{scenario.priority}</small>
              </div>
              <p>{scenario.type}</p>
              <ListBlock title="Preconditions" items={scenario.preconditions} compact />
              <ListBlock title="Steps" items={scenario.steps} compact ordered />
              <p className="expected"><strong>Expected:</strong> {scenario.expected_result}</p>
              <ListBlock title="Test Data" items={scenario.test_data} compact />
              <p className="automation">Automation candidate: {scenario.automation_candidate ? 'Yes' : 'No'}</p>
            </div>
          ))}
        </div>
      </section>
    </article>
  );
}

function ListBlock({ title, items = [], compact = false, ordered = false }) {
  const ListTag = ordered ? 'ol' : 'ul';

  return (
    <div className={compact ? 'list-block compact' : 'list-block'}>
      <h4>{title}</h4>
      {items?.length ? (
        <ListTag>
          {items.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ListTag>
      ) : (
        <p className="muted">None provided.</p>
      )}
    </div>
  );
}

function testPlanToMarkdown(payload, issue) {
  const plan = payload.test_plan || {};
  const lines = [
    `# ${plan.title || 'Generated Test Plan'}`,
    '',
    `Source issue: ${issue.key}`,
    `Summary: ${issue.summary}`,
    '',
    '## Objective',
    plan.objective || '',
    '',
    '## Scope',
    '### In Scope',
    ...markdownList(plan.scope?.in_scope),
    '',
    '### Out of Scope',
    ...markdownList(plan.scope?.out_of_scope),
    '',
    '## Assumptions',
    ...markdownList(plan.assumptions),
    '',
    '## Risks',
    ...markdownList(plan.risks),
    '',
    '## Test Scenarios'
  ];

  for (const scenario of plan.test_scenarios || []) {
    lines.push(
      '',
      `### ${scenario.id}: ${scenario.title}`,
      `Priority: ${scenario.priority}`,
      `Type: ${scenario.type}`,
      '',
      'Preconditions:',
      ...markdownList(scenario.preconditions),
      '',
      'Steps:',
      ...markdownList(scenario.steps, true),
      '',
      `Expected result: ${scenario.expected_result}`,
      '',
      'Test data:',
      ...markdownList(scenario.test_data),
      '',
      `Automation candidate: ${scenario.automation_candidate ? 'Yes' : 'No'}`
    );
  }

  return lines.join('\n');
}

function markdownList(items = [], ordered = false) {
  if (!items?.length) return ['- None provided.'];
  return items.map((item, index) => (ordered ? `${index + 1}. ${item}` : `- ${item}`));
}
