import { useState, useEffect, ReactNode } from "react";

import { AuthContext } from "./AuthContext";
import { User, Game } from "../types";

export const AuthProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [games, setGames] = useState<Game[]>([]);

  const fetchUser = () => {
    fetch("/api/user/me", {
      credentials: "include",
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Invalid token");
        }
        return response.json();
      })
      .then((data) => {
        setUser(data.user);
        setGames(data.games);
        setLoading(false);
      })
      .catch((error) => {
        console.error("Error validating token:", error);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchUser();
  }, []);

  return (
    <AuthContext.Provider value={{ loading, user, setUser, games, setGames }}>
      {children}
    </AuthContext.Provider>
  );
};
