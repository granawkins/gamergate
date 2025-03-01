import React, { createContext } from "react";

import { User, Game } from "../types";

interface AuthContextType {
  loading: boolean;
  user: User | null;
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
  games: Game[];
  setGames: React.Dispatch<React.SetStateAction<Game[]>>;
}

export const AuthContext = createContext<AuthContextType | undefined>(
  undefined,
);
