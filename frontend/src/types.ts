export interface User {
  id: string;
  email: string;
  username: string;
  created_at: string;
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