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

  const handleNameSave = () => {
    // In the future, this will send the updated name to the backend
    setIsEditing(false);
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
                      style={{
                        padding: "4px 8px",
                        backgroundColor: "#0084ff",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer",
                      }}
                    >
                      Save
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
