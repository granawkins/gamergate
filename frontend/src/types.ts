export interface User {
  id: string;
  created_at: string;
  messages_left: number;
  email?: string;
  username?: string;
  avatar_id?: string;
}

export interface Game {
  id: string;
  name: string;
  description?: string;
  path: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  parent_name: string | null;
  is_template?: boolean;
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
