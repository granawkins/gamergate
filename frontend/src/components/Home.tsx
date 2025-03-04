import { useState, useEffect } from "react";

import useAuth from "../auth/useAuth";
import { Game } from "../types";

// Modal component for cloning a game
const CloneGameModal = ({
  game,
  onClose,
  onClone,
}: {
  game: Game | null;
  onClose: () => void;
  onClone: (gameName: string, newName: string) => Promise<void>;
}) => {
  const [newName, setNewName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!game) return;

    if (!newName.trim()) {
      setError("Game name cannot be empty");
      return;
    }

    setIsSubmitting(true);
    setError("");

    try {
      await onClone(game.name, newName);
      // The redirect will be handled by the onClone function
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setIsSubmitting(false);
    }
  };

  if (!game) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.5)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          backgroundColor: "white",
          padding: "20px",
          borderRadius: "5px",
          width: "400px",
          maxWidth: "90%",
        }}
      >
        <h2>Clone Game</h2>
        <p>Create a new game based on "{game.name}"</p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "15px" }}>
            <label
              htmlFor="newGameName"
              style={{ display: "block", marginBottom: "5px" }}
            >
              New Game Name:
            </label>
            <input
              id="newGameName"
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
              }}
              autoFocus
            />
          </div>

          {error && (
            <div
              style={{
                color: "red",
                marginBottom: "15px",
              }}
            >
              {error}
            </div>
          )}

          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "10px",
            }}
          >
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              style={{
                padding: "8px 16px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                backgroundColor: "#f5f5f5",
                cursor: isSubmitting ? "not-allowed" : "pointer",
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                padding: "8px 16px",
                border: "1px solid #0066cc",
                borderRadius: "4px",
                backgroundColor: "#0084ff",
                color: "white",
                cursor: isSubmitting ? "not-allowed" : "pointer",
              }}
            >
              {isSubmitting ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Reusable game card component
const GameCard = ({
  game,
  linkPrefix,
  showDeleteButton = false,
  onDelete,
  onClone,
}: {
  game: Game;
  linkPrefix: string;
  showDeleteButton?: boolean;
  onDelete?: (game: Game) => void;
  onClone?: (game: Game) => void;
}) => {
  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onDelete) {
      onDelete(game);
    }
  };

  const handleCloneClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onClone) {
      onClone(game);
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
      {/* Clone button (remix icon) */}
      <button
        onClick={handleCloneClick}
        style={{
          position: "absolute",
          top: "8px",
          right: "8px",
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: "1.2rem",
          padding: "4px",
        }}
        title="Clone game"
      >
        🔄
      </button>
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
  const [gameToClone, setGameToClone] = useState<Game | null>(null);

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
      `Are you sure you want to delete "${game.name}"? This action is irreversible.`,
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

  const handleCloneGame = (game: Game) => {
    if (!user) {
      alert("Please log in to clone games");
      return;
    }
    setGameToClone(game);
  };

  const handleCloseModal = () => {
    setGameToClone(null);
  };

  const handleCloneSubmit = async (gameName: string, newName: string) => {
    try {
      const response = await fetch(`/api/games/${gameName}/clone`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ new_name: newName }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to clone game");
      }

      const data = await response.json();

      // Add the new game to the user's games list
      if (data.game) {
        setGames([...userGames, data.game]);
      }

      // Redirect to the editor page for the new game
      if (data.redirect) {
        window.location.href = data.redirect;
      }
    } catch (error) {
      console.error("Error cloning game:", error);
      throw error;
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
              onClone={handleCloneGame}
            />
          ))}
        </div>
      )}

      <h2>Play</h2>
      <div style={gameGridStyle}>
        {publicGames.map((game) => (
          <GameCard
            key={game.id}
            game={game}
            linkPrefix="/play"
            onClone={handleCloneGame}
          />
        ))}
      </div>

      {/* Clone Game Modal */}
      {gameToClone && (
        <CloneGameModal
          game={gameToClone}
          onClose={handleCloseModal}
          onClone={handleCloneSubmit}
        />
      )}
    </div>
  );
};
