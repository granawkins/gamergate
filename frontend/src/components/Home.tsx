import { useState, useEffect } from "react";

import useAuth from "../auth/useAuth";
import { Game } from "../types";

export const Home = () => {
  const { user } = useAuth();
  const [games, setGames] = useState<Game[]>([]);

  const fetchGames = async () => {
    const response = await fetch("/api/games");
    const data = await response.json();
    setGames(data);
  };

  useEffect(() => {
    fetchGames();
  }, []);

  return (
    <div>
      {!user && <h2>Login to create games</h2>}
      <h2>Play</h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {games.map((game) => (
          <a
            href={`/play/${game.name}`}
            key={game.id}
            style={{
              height: "180px",
              width: "180px",
              border: "1px solid black",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <h3>{game.name}</h3>
          </a>
        ))}
      </div>
    </div>
  );
};
