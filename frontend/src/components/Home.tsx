import { useState, useEffect } from "react";

import useAuth from "../auth/useAuth";
import { Game } from "../types";

// Reusable game card component
const GameCard = ({ 
  game, 
  linkPrefix, 
  showDeleteButton = false,
  onDelete
}: { 
  game: Game; 
  linkPrefix: string;
  showDeleteButton?: boolean;
  onDelete?: (game: Game) => void;
}) => {
  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onDelete) {
      onDelete(game);
    }
  };

  return (
    <a
      href={`${linkPrefix}/${game.name}`}
      key={game.id}
      style={{
        position: "relative",
        height: "180px",
        width: "180px",
        border: "1px solid black",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <h3>{game.name}</h3>
      {showDeleteButton && (
        <button
          onClick={handleDeleteClick}
          style={{
            position: "absolute",
            bottom: "8px",
            right: "8px",
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "1.2rem",
            padding: "4px",
          }}
          title="Delete game"
        >
          🗑️
        </button>
      )}
    </a>
  );
};

export const Home = () => {
  const { user, games: userGames, setGames } = useAuth();
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

  const handleDeleteGame = async (game: Game) => {
    // Show confirmation dialog
    const confirmed = window.confirm(
      `Are you sure you want to delete "${game.name}"? This action is irreversible.`
    );
    
    if (!confirmed) return;

    try {
      const response = await fetch(`/api/games/${game.name}`, {
        method: "DELETE",
      });

      if (response.ok) {
        // Update the games list in AuthContext
        setGames(userGames.filter((g) => g.id !== game.id));
      } else {
        console.error("Failed to delete game:", await response.text());
        alert("Failed to delete game. Please try again.");
      }
    } catch (error) {
      console.error("Error deleting game:", error);
      alert("An error occurred while deleting the game. Please try again.");
    }
  };

  return (
    <div>
      <h2>Create</h2>
      {!user ? (
        <p>Login to create games</p>
      ) : userGames.length === 0 ? (
        <p>Create a new game by remixing an existing game</p>
      ) : (
        <div style={gameGridStyle}>
          {userGames.map((game) => (
            <GameCard 
              key={game.id} 
              game={game} 
              linkPrefix="/editor" 
              showDeleteButton={true}
              onDelete={handleDeleteGame}
            />
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
