import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Game } from "../types";

interface GameInfoTabProps {
  gameInfo: Game | null;
  isLoading: boolean;
}

export const GameInfoTab = ({ gameInfo, isLoading }: GameInfoTabProps) => {
  const [editableName, setEditableName] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [parentName, setParentName] = useState<string | null>(null);
  const [isLoadingParent, setIsLoadingParent] = useState(false);
  const [isCheckingName, setIsCheckingName] = useState(false);

  // Format date to a more readable format
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  // Fetch parent game name when parent_id changes
  useEffect(() => {
    const fetchParentName = async () => {
      if (!gameInfo?.parent_id) return;

      setIsLoadingParent(true);
      try {
        const response = await fetch(`/api/games/${gameInfo.parent_id}`);
        if (!response.ok) {
          throw new Error("Failed to fetch parent game");
        }
        const data = await response.json();
        setParentName(data.name);
      } catch (error) {
        console.error("Error fetching parent game:", error);
        setParentName(null);
      } finally {
        setIsLoadingParent(false);
      }
    };

    fetchParentName();
  }, [gameInfo?.parent_id]);

  // Initialize editable name when gameInfo changes
  useEffect(() => {
    if (gameInfo) {
      setEditableName(gameInfo.name);
    }
  }, [gameInfo]);

  const handleNameEdit = () => {
    setIsEditing(true);
  };

  const handleNameCancel = () => {
    // Reset to original name and exit edit mode
    if (gameInfo) {
      setEditableName(gameInfo.name);
    }
    setIsEditing(false);
  };

  const handleNameSave = async () => {
    if (!gameInfo) return;

    // Don't save if name is empty
    if (!editableName.trim()) {
      alert("Game name cannot be empty");
      return;
    }

    // Don't save if name hasn't changed
    if (editableName === gameInfo.name) {
      setIsEditing(false);
      return;
    }

    // Check if the name is unique
    setIsCheckingName(true);
    try {
      const response = await fetch("/api/games/check-name", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: editableName,
          current_game_id: gameInfo.id,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to check game name");
      }

      const data = await response.json();

      if (!data.available) {
        alert(
          `The name "${editableName}" is already taken. Please choose a different name.`,
        );
        return;
      }

      // In the future, this will send the updated name to the backend
      setIsEditing(false);
    } catch (error) {
      console.error("Error checking game name:", error);
      alert("Failed to check if the name is available. Please try again.");
    } finally {
      setIsCheckingName(false);
    }
  };

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEditableName(e.target.value);
  };

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "1rem",
      }}
    >
      {isLoading ? (
        <div
          style={{
            textAlign: "center",
            color: "#888",
            marginTop: "2rem",
          }}
        >
          Loading game information...
        </div>
      ) : gameInfo ? (
        <div>
          <h2>Game Information</h2>
          <div style={{ marginTop: "1rem" }}>
            {/* Name (Editable) */}
            <div
              style={{
                display: "flex",
                padding: "0.5rem 0",
                borderBottom: "1px solid #eee",
              }}
            >
              <div
                style={{
                  fontWeight: "bold",
                  width: "120px",
                  flexShrink: 0,
                }}
              >
                Name:
              </div>
              <div style={{ display: "flex", alignItems: "center", flex: 1 }}>
                {isEditing ? (
                  <>
                    <input
                      type="text"
                      value={editableName}
                      onChange={handleNameChange}
                      style={{
                        padding: "4px 8px",
                        border: "1px solid #ccc",
                        borderRadius: "4px",
                        marginRight: "8px",
                      }}
                      autoFocus
                    />
                    <button
                      onClick={handleNameSave}
                      disabled={isCheckingName}
                      style={{
                        padding: "4px 8px",
                        backgroundColor: "#0084ff",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: isCheckingName ? "default" : "pointer",
                        opacity: isCheckingName ? 0.7 : 1,
                        marginRight: "8px",
                      }}
                    >
                      {isCheckingName ? "Checking..." : "Save"}
                    </button>
                    <button
                      onClick={handleNameCancel}
                      disabled={isCheckingName}
                      style={{
                        padding: "4px 8px",
                        backgroundColor: "#f0f0f0",
                        border: "1px solid #ccc",
                        borderRadius: "4px",
                        cursor: isCheckingName ? "default" : "pointer",
                        opacity: isCheckingName ? 0.7 : 1,
                      }}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <span style={{ marginRight: "8px" }}>{gameInfo.name}</span>
                    <button
                      onClick={handleNameEdit}
                      style={{
                        padding: "4px 8px",
                        backgroundColor: "#f0f0f0",
                        border: "1px solid #ccc",
                        borderRadius: "4px",
                        cursor: "pointer",
                      }}
                    >
                      Edit
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Parent Game */}
            <div
              style={{
                display: "flex",
                padding: "0.5rem 0",
                borderBottom: "1px solid #eee",
              }}
            >
              <div
                style={{
                  fontWeight: "bold",
                  width: "120px",
                  flexShrink: 0,
                }}
              >
                Parent Game:
              </div>
              <div>
                {isLoadingParent ? (
                  "Loading parent..."
                ) : parentName ? (
                  <Link
                    to={`/play/${parentName}`}
                    style={{
                      color: "#0084ff",
                      textDecoration: "none",
                    }}
                  >
                    {parentName}
                  </Link>
                ) : (
                  gameInfo.parent_id || "None"
                )}
              </div>
            </div>

            {/* Created At */}
            <div
              style={{
                display: "flex",
                padding: "0.5rem 0",
                borderBottom: "1px solid #eee",
              }}
            >
              <div
                style={{
                  fontWeight: "bold",
                  width: "120px",
                  flexShrink: 0,
                }}
              >
                Created At:
              </div>
              <div>{formatDate(gameInfo.created_at)}</div>
            </div>

            {/* Updated At */}
            <div
              style={{
                display: "flex",
                padding: "0.5rem 0",
                borderBottom: "1px solid #eee",
              }}
            >
              <div
                style={{
                  fontWeight: "bold",
                  width: "120px",
                  flexShrink: 0,
                }}
              >
                Updated At:
              </div>
              <div>{formatDate(gameInfo.updated_at)}</div>
            </div>

            {/* Plays */}
            <div
              style={{
                display: "flex",
                padding: "0.5rem 0",
                borderBottom: "1px solid #eee",
              }}
            >
              <div
                style={{
                  fontWeight: "bold",
                  width: "120px",
                  flexShrink: 0,
                }}
              >
                Plays:
              </div>
              <div>{gameInfo.plays}</div>
            </div>
          </div>
        </div>
      ) : (
        <div
          style={{
            textAlign: "center",
            color: "#888",
            marginTop: "2rem",
          }}
        >
          Failed to load game information
        </div>
      )}
    </div>
  );
};
