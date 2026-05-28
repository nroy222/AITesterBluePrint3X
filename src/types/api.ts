export interface CreateUserPayload {
  name: string;
  job?: string;
  username?: string;
  email?: string;
  [key: string]: unknown;
}

export interface CreateUserResponse {
  id: number;
  name?: string;
  job?: string;
  username?: string;
  email?: string;
  createdAt?: string;
  [key: string]: unknown;
}

export interface UserData {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  avatar: string;
}

export interface SingleUserResponse {
  data: UserData;
}
