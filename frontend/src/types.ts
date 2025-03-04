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
  owner_id: string;
  created_at: string;
  updated_at: string;
  plays: number;
  parent_name: string | null;
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
