import React, { createContext, useState, ReactNode, useEffect } from 'react';

import { User, Game } from './types';

interface AuthContextType {
  loading: boolean;
  user: User | null;
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
  games: Game[];
  setGames: React.Dispatch<React.SetStateAction<Game[]>>;
}

export const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [games, setGames] = useState<Game[]>([]);

  const fetchUser = () => {
    fetch('/api/user/me', {
      credentials: 'include',
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Invalid token');
        }
        return response.json();
      })
      .then((data) => {
        setUser(data.user);
        setGames(data.games);
        setLoading(false);
      })
      .catch((error) => {
        console.error('Error validating token:', error);
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
