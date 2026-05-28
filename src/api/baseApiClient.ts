import { APIRequestContext, APIResponse } from '@playwright/test';
import { config } from '../config/env';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export class BaseApiClient {
  constructor(
    private readonly request: APIRequestContext,
    private readonly baseUrl: string = config.baseUrl,
  ) {}

  private log(message: string): void {
    console.info(`[API] ${message}`);
  }

  private async requestWithHandling(
    method: HttpMethod,
    path: string,
    options: Record<string, unknown> = {},
  ): Promise<APIResponse> {
    const url = `${this.baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
    this.log(`${method} ${url}`);

    try {
      const response = await this.request.fetch(url, {
        method,
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          ...(options.headers as Record<string, string> | undefined),
        },
        data: options.data,
        params: options.params as Record<string, string> | undefined,
        timeout: config.timeoutMs,
      });

      this.log(`${method} ${url} -> ${response.status()} ${response.statusText()}`);

      if (!response.ok()) {
        const body = await response.text();
        throw new Error(`Request failed with ${response.status()}: ${body}`);
      }

      return response;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`API request error for ${method} ${url}: ${message}`);
    }
  }

  async get(path: string, options: Record<string, unknown> = {}): Promise<APIResponse> {
    return this.requestWithHandling('GET', path, options);
  }

  async post(path: string, data: unknown, options: Record<string, unknown> = {}): Promise<APIResponse> {
    return this.requestWithHandling('POST', path, { ...options, data });
  }

  async put(path: string, data: unknown, options: Record<string, unknown> = {}): Promise<APIResponse> {
    return this.requestWithHandling('PUT', path, { ...options, data });
  }

  async patch(path: string, data: unknown, options: Record<string, unknown> = {}): Promise<APIResponse> {
    return this.requestWithHandling('PATCH', path, { ...options, data });
  }

  async delete(path: string, options: Record<string, unknown> = {}): Promise<APIResponse> {
    return this.requestWithHandling('DELETE', path, options);
  }
}
