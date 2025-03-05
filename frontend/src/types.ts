export interface User {
  id: string;
  email: string;
  username: string;
  created_at: string;
  avatar_id?: string;
  messages_left: number;
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
  minutes_played?: number;
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

export interface PlaySession {
  id: string;
  user_id: string;
  game_id: string;
  seconds_played: number;
  timestamp: string;
}
