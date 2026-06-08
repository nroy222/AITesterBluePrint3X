import { safeReadText } from './safeReadText.js';

export async function createTestPlan(groq, issue) {
  const response = await fetch(`${groq.baseUrl.replace(/\/+$/, '')}/chat/completions`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${groq.apiKey}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: groq.model,
      temperature: 0.15,
      messages: [
        {
          role: 'system',
          content: [
            'You are a senior QA test architect.',
            'Create a native, practical manual QA test plan from Jira issue data.',
            'Return only valid JSON. No markdown. No surrounding prose.',
            'Do not invent requirements as facts. Put uncertainty in assumptions or risks.'
          ].join(' ')
        },
        {
          role: 'user',
          content: JSON.stringify({
            instruction: 'Generate a complete test plan with positive, negative, edge, regression, and data validation scenarios.',
            output_schema: testPlanSchema(),
            jira_issue: issue
          })
        }
      ]
    })
  });

  if (!response.ok) {
    const body = await safeReadText(response);
    const error = new Error(`Groq generation failed (${response.status}): ${body || response.statusText}`);
    error.status = response.status;
    throw error;
  }

  const payload = await readJsonResponse(response, 'Groq');
  const content = payload.choices?.[0]?.message?.content;

  if (!content) {
    throw new Error('Groq response did not include generated content.');
  }

  return normalizeTestPlan(parseModelJson(content), issue);
}

function testPlanSchema() {
  return {
    test_plan: {
      title: 'string',
      source_issue: 'string',
      objective: 'string',
      scope: {
        in_scope: ['string'],
        out_of_scope: ['string']
      },
      assumptions: ['string'],
      risks: ['string'],
      test_scenarios: [
        {
          id: 'TP-001',
          title: 'string',
          priority: 'High | Medium | Low',
          type: 'Functional | Negative | Edge | Regression | Security | Usability | Data Validation',
          preconditions: ['string'],
          steps: ['string'],
          expected_result: 'string',
          test_data: ['string'],
          automation_candidate: true
        }
      ],
      traceability: [
        {
          jira_field: 'string',
          covered_by: ['TP-001']
        }
      ]
    }
  };
}

async function readJsonResponse(response, serviceName) {
  const body = await safeReadText(response);

  try {
    return JSON.parse(body);
  } catch {
    const error = new Error(`${serviceName} returned a non-JSON response. Check the API base URL, key, and model access.`);
    error.status = 502;
    throw error;
  }
}

function normalizeTestPlan(payload, issue) {
  const plan = payload.test_plan || payload;
  return {
    test_plan: {
      title: plan.title || `Test Plan for ${issue.key}`,
      source_issue: plan.source_issue || issue.key,
      objective: plan.objective || `Validate ${issue.summary}`,
      scope: {
        in_scope: ensureArray(plan.scope?.in_scope),
        out_of_scope: ensureArray(plan.scope?.out_of_scope)
      },
      assumptions: ensureArray(plan.assumptions),
      risks: ensureArray(plan.risks),
      test_scenarios: ensureArray(plan.test_scenarios).map((scenario, index) => ({
        id: scenario.id || `TP-${String(index + 1).padStart(3, '0')}`,
        title: scenario.title || 'Untitled scenario',
        priority: scenario.priority || 'Medium',
        type: scenario.type || 'Functional',
        preconditions: ensureArray(scenario.preconditions),
        steps: ensureArray(scenario.steps),
        expected_result: scenario.expected_result || '',
        test_data: ensureArray(scenario.test_data),
        automation_candidate: Boolean(scenario.automation_candidate)
      })),
      traceability: ensureArray(plan.traceability)
    }
  };
}

function parseModelJson(content) {
  try {
    return JSON.parse(content);
  } catch {
    const match = content.match(/\{[\s\S]*\}/);
    if (!match) {
      throw new Error('Groq response was not valid JSON.');
    }
    return JSON.parse(match[0]);
  }
}

function ensureArray(value) {
  if (!value) return [];
  return Array.isArray(value) ? value : [String(value)];
}
