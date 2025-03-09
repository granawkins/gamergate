import { useState } from "react";
import { Modal } from "./Modal";
import { Game } from "../types";

interface GameInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  game: Game | null;
}

export const GameInfoModal: React.FC<GameInfoModalProps> = ({
  isOpen,
  onClose,
  game,
}) => {
  const [newName, setNewName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!game) return null;

  const handleClone = async () => {
    if (!newName.trim()) {
      setError("Game name cannot be empty");
      return;
    }

    setIsSubmitting(true);
    setError("");

    try {
      const response = await fetch(`/api/games/${game.name}/clone`, {
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

      // Redirect to the editor page for the new game
      if (data.redirect) {
        window.location.href = data.redirect;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setIsSubmitting(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={game.name}>
      <p>{game.description || "No description available."}</p>
      <hr />
      <div className="info-section">
        <div className="info-style">
          <span>Seconds Played</span>
          <span>{game.seconds_played || "None"}</span>
        </div>

        <div className="info-style">
          <span>Created By</span>
          <span>{game.owner_username || "Anonymous"}</span>
        </div>

        {game.parent_name && (
          <div className="info-style">
            <span>Based On</span>
            <a
              href={`/play/${game.parent_name}`}
              style={{
                color: "var(--primary-color)",
                textDecoration: "none",
              }}
            >
              {game.parent_name}
            </a>
          </div>
        )}

        <div className="info-style">
          <span>Created</span>
          <span>{formatDate(game.created_at)}</span>
        </div>

        <div className="info-style">
          <span>Last Updated</span>
          <span>{formatDate(game.updated_at)}</span>
        </div>
      </div>

      <hr />

      <p style={{ marginBottom: "1rem" }}>Clone This Game</p>
      <div className="info-style">
        <input
          id="newGameName"
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New Game Name"
          style={{
            width: "100%",
          }}
        />
        <button
          onClick={handleClone}
          disabled={isSubmitting}
          className="primary"
          style={{
            cursor: isSubmitting ? "not-allowed" : "pointer",
            width: "180px",
          }}
        >
          {isSubmitting ? "Creating..." : "Clone Game"}
        </button>

        {error && (
          <div style={{ color: "red", marginBottom: "1rem" }}>{error}</div>
        )}
      </div>
    </Modal>
  );
};
