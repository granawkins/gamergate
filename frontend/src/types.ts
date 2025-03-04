export interface User {
  id: string;
  email: string;
  username: string;
  created_at: string;
  avatar_id?: string;
}

export interface Game {
  id: string;
  name: string;
  path: string;
  owner_id: string;
  parent_id: string;
  created_at: string;
  updated_at: string;
  plays: number;
}

export interface Message {
  id: string;
  text: string;
  role: "user" | "assistant";
  timestamp: string;
  cost?: number;
  status?: "processing" | "completed" | "error";
  commit_sha?: string;
}
