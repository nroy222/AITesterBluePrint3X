import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { BaseApiClient } from '../../src/api/baseApiClient';
import { UsersApi } from '../../src/api/services/usersApi';

function loadJsonFixture(fileName: string): Record<string, unknown> {
  const fixturePath = path.resolve(__dirname, '../../fixtures/users', fileName);
  return JSON.parse(fs.readFileSync(fixturePath, 'utf8')) as Record<string, unknown>;
}

test.describe('Users API workflow', () => {
  test('creates a user and fetches the same user', async ({ request }) => {
    const api = new BaseApiClient(request);
    const usersApi = new UsersApi(api);

    const payload = loadJsonFixture('create-user.json');
    const uniqueName = `QA Automation ${Date.now()}`;
    const requestPayload = {
      ...payload,
      name: uniqueName,
      username: `qa_automation_${Date.now()}`,
      email: `qa_${Date.now()}@example.com`,
    };

    const createResponse = await usersApi.createUser(requestPayload);

    expect(createResponse.status()).toBe(201);
    const createdBody = await createResponse.json();

    expect(createdBody).toHaveProperty('id');
    expect(createdBody.name).toBe(uniqueName);
    expect(createdBody.username).toBe(requestPayload.username);
    expect(createdBody.email).toBe(requestPayload.email);

    const getResponse = await usersApi.getUser('1');

    expect(getResponse.status()).toBe(200);
    const fetchedBody = await getResponse.json();

    expect(fetchedBody.id).toBe(1);
    expect(fetchedBody.name).toBe('Leanne Graham');
    expect(fetchedBody.email).toBe('Sincere@april.biz');
  });
});
