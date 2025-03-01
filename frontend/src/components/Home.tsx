import { useState, useEffect } from "react";

import useAuth from "../auth/useAuth";
import { Game } from "../types";

// Reusable game card component
const GameCard = ({ game, linkPrefix }: { game: Game; linkPrefix: string }) => (
  <a
    href={`${linkPrefix}/${game.name}`}
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
);

export const Home = () => {
  const { user, games: userGames } = useAuth();
  const [publicGames, setPublicGames] = useState<Game[]>([]);

  const fetchPublicGames = async () => {
    const response = await fetch("/api/games");
    const data = await response.json();
    setPublicGames(data);
  };

  useEffect(() => {
    fetchPublicGames();
  }, []);

  // Shared style for game grid
  const gameGridStyle = {
    display: "flex",
    flexWrap: "wrap" as const,
    gap: "1rem",
    marginBottom: "2rem",
  };

  return (
    <div>
      <h2>Create</h2>
      {!user ? (
        <p>Login to create games</p>
      ) : userGames.length === 0 ? (
        <p>You haven't created any games yet</p>
      ) : (
        <div style={gameGridStyle}>
          {userGames.map((game) => (
            <GameCard key={game.id} game={game} linkPrefix="/editor" />
          ))}
        </div>
      )}

      <h2>Play</h2>
      <div style={gameGridStyle}>
        {publicGames.map((game) => (
          <GameCard key={game.id} game={game} linkPrefix="/play" />
        ))}
      </div>
    </div>
  );
};
