import { useState, useEffect } from "react";
import { Info } from "./Info";
import useAuth from "../auth/useAuth";
import { Game } from "../types";
import { Modal } from "./Modal";

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

  return (
    <Modal isOpen={!!game} onClose={onClose} title="Clone Game">
      {game && (
        <>
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
              <button type="button" onClick={onClose} disabled={isSubmitting}>
                Cancel
              </button>
              <button type="submit" disabled={isSubmitting} className="primary">
                {isSubmitting ? "Creating..." : "Create"}
              </button>
            </div>
          </form>
        </>
      )}
    </Modal>
  );
};

// Reusable game card component
const GameCard = ({
  game,
  linkPrefix,
  showDeleteButton = false,
  onDelete,
  onClone,
  isTemplate = false,
}: {
  game: Game;
  linkPrefix: string;
  showDeleteButton?: boolean;
  onDelete?: (game: Game) => void;
  onClone?: (game: Game) => void;
  isTemplate?: boolean;
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

  const handleCardClick = (e: React.MouseEvent) => {
    // For templates, clicking the card should trigger the clone action
    if (isTemplate && onClone) {
      e.preventDefault();
      onClone(game);
    }
  };

  return (
    <a
      href={`${linkPrefix}/${game.name}`}
      key={game.id}
      onClick={handleCardClick}
      style={{
        position: "relative",
        height: "180px",
        width: "180px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        alignItems: "center",
        cursor: isTemplate ? "pointer" : "default",
        overflow: "hidden",
        textDecoration: "none",
        color: "inherit",
        border: "1px solid #ccc",
      }}
    >
      {game.cover_image ? (
        <div
          style={{
            width: "100%",
            height: "120px",
            overflow: "hidden",
            position: "relative",
          }}
        >
          <img
            src={game.cover_image}
            alt={`Cover for ${game.name}`}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
          />
        </div>
      ) : (
        <div
          style={{
            width: "100%",
            height: "120px",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: "2rem", color: "#ccc" }}>🎮</span>
        </div>
      )}
      <div
        style={{
          padding: "8px",
          textAlign: "center",
          width: "100%",
          backgroundColor: "rgba(0, 0, 0, 0.9)",
        }}
      >
        <h3
          style={{
            margin: "0",
            fontSize: "16px",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {game.name}
        </h3>
      </div>
      {/* Clone button (remix icon) - not shown for templates */}
      {!isTemplate && (
        <button
          onClick={handleCloneClick}
          style={{
            position: "absolute",
            top: "8px",
            right: "8px",
            background: "transparent",
            cursor: "pointer",
            fontSize: "1.2rem",
            padding: "4px",
            width: "30px",
            height: "30px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title="Clone game"
        >
          🔄
        </button>
      )}
      {showDeleteButton && (
        <button
          onClick={handleDeleteClick}
          style={{
            position: "absolute",
            bottom: "8px",
            right: "8px",
            background: "transparent",
            cursor: "pointer",
            fontSize: "1.2rem",
            padding: "4px",
            width: "30px",
            height: "30px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
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
  const [templates, setTemplates] = useState<Game[]>([]);
  const [gameToClone, setGameToClone] = useState<Game | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [sortOption, setSortOption] = useState<string>("newest");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [showInfo, setShowInfo] = useState(false);

  const fetchGames = async (query = "", sort = "newest") => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/games?search=${query}&sort=${sort}`);
      const data = await response.json();

      // Assume the new format is always used
      setPublicGames(data.play);
      setTemplates(data.templates);
    } catch (error) {
      console.error("Error fetching games:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGames(searchQuery, sortOption);
  }, [searchQuery, sortOption]);

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
    if (!user || !user.email) {
      alert("Please log in to clone games");
      return;
    }
    setGameToClone(game);
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
    <div
      style={{
        margin: 0,
        display: "flex",
        flexDirection: "column",
        minHeight: "calc(100vh - 90px)", // Adjusting for header height
      }}
    >
      <div style={{ flex: "1 0 auto", padding: "0 1rem" }}>
        <h2>Create</h2>
        {!user || !user.email ? (
          <p>Login to create games</p>
        ) : (
          <>
            <div style={gameGridStyle}>
              {/* User's games */}
              {userGames.length > 0 &&
                userGames.map((game) => (
                  <GameCard
                    key={game.id}
                    game={game}
                    linkPrefix="/editor"
                    showDeleteButton={true}
                    onDelete={handleDeleteGame}
                    onClone={handleCloneGame}
                  />
                ))}

              {/* Templates - always shown for logged-in users */}
              {templates.map((template) => (
                <GameCard
                  key={template.id}
                  game={template}
                  linkPrefix="/editor"
                  onClone={handleCloneGame}
                  isTemplate={true}
                />
              ))}
            </div>
          </>
        )}

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "1rem",
          }}
        >
          <h2>Play</h2>
          <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
            <input
              type="text"
              placeholder="Search games..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                padding: "0.5rem",
                borderRadius: "4px",
                border: "1px solid #ccc",
                width: "200px",
              }}
            />
            <div style={{ display: "flex", gap: "0.5rem" }}>
              {[
                { label: "Newest", value: "newest" },
                { label: "Oldest", value: "oldest" },
                { label: "Most Played", value: "most_played" },
              ].map((option) => (
                <button
                  key={option.value}
                  onClick={() => setSortOption(option.value)}
                  style={{
                    textDecoration:
                      sortOption === option.value ? "underline" : "none",
                  }}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {isLoading ? (
          <div style={{ textAlign: "center", padding: "2rem" }}>
            Loading games...
          </div>
        ) : publicGames.length === 0 ? (
          <div style={{ textAlign: "center", padding: "2rem" }}>
            {searchQuery
              ? "No games found matching your search."
              : "No games available."}
          </div>
        ) : (
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
        )}
      </div>

      {/* Footer */}
      <footer
        style={{
          width: "100%",
          borderTop: "1px solid #ccc",
          padding: "1rem",
          margin: 0,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          boxSizing: "border-box",
          height: "40px",
        }}
      >
        <div>
          <span>
            &copy; 2025{" "}
            <a
              href="https://twitter.com/granawkins"
              target="_blank"
              rel="noopener noreferrer"
              style={{ textDecoration: "none", color: "#0084ff" }}
            >
              @granawkins
            </a>
          </span>
        </div>
        <div>
          <a
            onClick={() => setShowInfo(true)}
            style={{ fontSize: "1.5rem", cursor: "pointer" }}
          >
            ⓘ
          </a>
        </div>
      </footer>

      {/* Info modal */}
      {showInfo && <Info onClose={() => setShowInfo(false)} />}

      {/* Clone Game Modal */}
      {gameToClone && (
        <CloneGameModal
          game={gameToClone}
          onClose={() => setGameToClone(null)}
          onClone={handleCloneSubmit}
        />
      )}
    </div>
  );
};
