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
      <div style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginBottom: "0.5rem" }}>Description</h3>
        <p>{game.description || "No description available."}</p>
      </div>

      <div style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginBottom: "0.5rem" }}>Seconds Played</h3>
        <p>{game.seconds_played || "None"}</p>
      </div>

      <div style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginBottom: "0.5rem" }}>Created By</h3>
        <p>{game.owner_username || "Anonymous"}</p>
      </div>

      {game.parent_name && (
        <div style={{ marginBottom: "1.5rem" }}>
          <h3 style={{ marginBottom: "0.5rem" }}>Based On</h3>
          <p>
            <a
              href={`/play/${game.parent_name}`}
              style={{
                color: "var(--primary-color)",
                textDecoration: "none",
              }}
            >
              {game.parent_name}
            </a>
          </p>
        </div>
      )}

      <div style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginBottom: "0.5rem" }}>Created</h3>
        <p>{formatDate(game.created_at)}</p>
      </div>

      <div style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginBottom: "0.5rem" }}>Last Updated</h3>
        <p>{formatDate(game.updated_at)}</p>
      </div>

      <div
        style={{
          borderTop: "1px solid var(--text-color)",
          paddingTop: "1.5rem",
        }}
      >
        <h3 style={{ marginBottom: "1rem" }}>Remix This Game</h3>
        <div style={{ marginBottom: "1rem" }}>
          <label
            htmlFor="newGameName"
            style={{ display: "block", marginBottom: "0.5rem" }}
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
              border: "1px solid var(--text-color)",
              borderRadius: "4px",
              backgroundColor: "var(--bg-color)",
              color: "var(--text-color)",
            }}
          />
        </div>

        {error && (
          <div style={{ color: "red", marginBottom: "1rem" }}>{error}</div>
        )}

        <button
          onClick={handleClone}
          disabled={isSubmitting}
          className="primary"
          style={{
            padding: "8px 16px",
            border: "none",
            borderRadius: "4px",
            cursor: isSubmitting ? "not-allowed" : "pointer",
            width: "100%",
          }}
        >
          {isSubmitting ? "Creating..." : "Remix Game"}
        </button>
      </div>
    </Modal>
  );
};
