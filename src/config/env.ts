import dotenv from 'dotenv';

dotenv.config();

export interface AppConfig {
  baseUrl: string;
  timeoutMs: number;
}

export const config: AppConfig = {
  baseUrl: process.env.API_BASE_URL || 'https://jsonplaceholder.typicode.com',
  timeoutMs: Number(process.env.API_TIMEOUT_MS || 60000),
};

export function getConfig(): AppConfig {
  return config;
}
