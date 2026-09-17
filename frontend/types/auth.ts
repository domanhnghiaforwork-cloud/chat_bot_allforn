export interface User {
  id: string;
  email: string;
  role: "user" | "admin";
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}
