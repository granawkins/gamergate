import { useState, useEffect } from "react";
import { Modal } from "./Modal";
import { Game } from "../types";
import useAuth from "../auth/useAuth";

export const GameInfoModal = ({
  gameName,
  onClose,
  onClone,
}: {
  gameName: string;
  onClose: () => void;
  onClone: (game: Game) => void;
}) => {
  const [game, setGame] = useState<Game | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    const fetchGameInfo = async () => {
      try {
        const response = await fetch(`/api/games/${gameName}/info`);
        if (!response.ok) {
          throw new Error("Failed to fetch game info");
        }
        const data = await response.json();
        setGame(data);
      } catch (error) {
        console.error("Error fetching game info:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchGameInfo();
  }, [gameName]);

  const handleLoginClick = () => {
    window.location.href = `/api/user/login?redirect=${encodeURIComponent(window.location.pathname)}`;
  };

  if (isLoading) {
    return (
      <Modal onClose={onClose}>
        <div style={{ textAlign: "center", padding: "1rem" }}>
          Loading game information...
        </div>
      </Modal>
    );
  }

  if (!game) {
    return (
      <Modal onClose={onClose}>
        <div style={{ textAlign: "center", color: "red", padding: "1rem" }}>
          Failed to load game information
        </div>
      </Modal>
    );
  }

  return (
    <Modal onClose={onClose}>
      <div style={{ minWidth: "300px" }}>
        <h2 style={{ marginBottom: "1rem", color: "#0084ff" }}>{game.name}</h2>

        <div style={{ marginBottom: "1rem" }}>
          <p style={{ fontWeight: "bold", marginBottom: "0.25rem" }}>
            Creator:
          </p>
          <p>{game.owner_id || "Unknown"}</p>
        </div>

        <div style={{ marginBottom: "1.5rem" }}>
          <p style={{ fontWeight: "bold", marginBottom: "0.25rem" }}>
            Description:
          </p>
          <p style={{ whiteSpace: "pre-wrap" }}>
            {game.description || "No description available."}
          </p>
        </div>

        {user && user.email ? (
          <button
            onClick={() => onClone(game)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 16px",
              backgroundColor: "#0084ff",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "1rem",
            }}
          >
            <span>🔄</span>
            Clone game
          </button>
        ) : (
          <a
            onClick={handleLoginClick}
            style={{
              display: "inline-block",
              padding: "8px 16px",
              backgroundColor: "#f0f0f0",
              border: "1px solid #ccc",
              borderRadius: "4px",
              textDecoration: "none",
              color: "#333",
              cursor: "pointer",
            }}
          >
            Login to clone
          </a>
        )}
      </div>
    </Modal>
  );
};
