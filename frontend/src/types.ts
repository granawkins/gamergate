export interface User {
  id: string;
  created_at: string;
  messages_left: number;
  email?: string;
  username?: string;
  avatar_id?: string;
  admin?: boolean;
}

export interface Game {
  id: string;
  name: string;
  description?: string;
  seconds_played?: number;
  path: string;
  owner_id: string;
  owner_username?: string;
  created_at: string;
  updated_at: string;
  parent_name: string | null;
  cover_image?: string;
  version?: number;
}

export interface Message {
  id: string;
  text: string;
  role: "user" | "assistant";
  timestamp: string;
  cost?: number;
  status?: "processing" | "completed" | "error";
  commit_sha?: string;
  model?: string;
  messages?: string; // admin only: serialized full messages
  processing_text?: string[]; // text from tool use messages
}
