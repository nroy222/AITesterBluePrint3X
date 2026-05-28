import { APIResponse } from '@playwright/test';
import { BaseApiClient } from '../baseApiClient';
import { CreateUserPayload, CreateUserResponse, SingleUserResponse } from '../../types/api';

export class UsersApi {
  constructor(private readonly api: BaseApiClient) {}

  async createUser(payload: CreateUserPayload): Promise<APIResponse> {
    return this.api.post('users', payload);
  }

  async getUser(userId: string): Promise<APIResponse> {
    return this.api.get(`users/${userId}`);
  }

  async parseCreateResponse(response: APIResponse): Promise<CreateUserResponse> {
    return (await response.json()) as CreateUserResponse;
  }

  async parseSingleUserResponse(response: APIResponse): Promise<SingleUserResponse> {
    return (await response.json()) as SingleUserResponse;
  }
}
