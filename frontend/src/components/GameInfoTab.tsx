import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Game } from "../types";

// EditableName component for handling name editing functionality
const EditableName = ({
  initialName,
  gameId,
}: {
  initialName: string;
  gameId: string;
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(initialName);
  const [isCheckingName, setIsCheckingName] = useState(false);

  // Update name when initialName changes
  useEffect(() => {
    setName(initialName);
  }, [initialName]);

  const handleCancel = () => {
    // Reset to original name and exit edit mode
    setName(initialName);
    setIsEditing(false);
  };

  const handleSave = async () => {
    // Don't save if name is empty
    if (!name.trim()) {
      alert("Game name cannot be empty");
      return;
    }

    // Don't save if name hasn't changed
    if (name === initialName) {
      setIsEditing(false);
      return;
    }

    // Check if the name is unique and update it if it is
    setIsCheckingName(true);
    try {
      const response = await fetch("/api/games/check-name", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name, current_game_id: gameId }),
      });

      if (!response.ok) {
        throw new Error("Failed to check game name");
      }

      const data = await response.json();

      // Handle the new response format
      if (data.successful === false) {
        alert(
          `The name "${name}" is already taken. Please choose a different name.`,
        );
        return;
      }

      // If the update was successful, reload the page with the new URL
      if (data.successful === true) {
        setIsEditing(false);
        // Redirect to the new URL
        const currentPath = window.location.pathname;
        const pathParts = currentPath.split("/");

        // Replace the game name in the URL
        if (pathParts.length >= 3 && pathParts[1] === "editor") {
          pathParts[2] = name;
          const newPath = pathParts.join("/");
          window.location.href = window.location.origin + newPath;
          return;
        }
      }

      // Handle backward compatibility or other cases
      setIsEditing(false);
    } catch (error) {
      console.error("Error checking/updating game name:", error);
      alert("Failed to update the game name. Please try again.");
    } finally {
      setIsCheckingName(false);
    }
  };

  if (isEditing) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flex: 1,
          flexWrap: "wrap", // Allow wrapping on mobile
          gap: "8px", // Add spacing between wrapped items
        }}
      >
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{
            padding: "4px 8px",
            border: "1px solid #ccc",
            borderRadius: "4px",
            flexGrow: 1,
            minWidth: "120px", // Ensure input has reasonable minimum width
            marginRight: "8px",
          }}
          autoFocus
        />
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={handleSave}
            disabled={isCheckingName}
            style={{
              padding: "4px 8px",
              backgroundColor: "#0084ff",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: isCheckingName ? "default" : "pointer",
              opacity: isCheckingName ? 0.7 : 1,
            }}
          >
            {isCheckingName ? "Checking..." : "Save"}
          </button>
          <button
            onClick={handleCancel}
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
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        flex: 1,
        flexWrap: "wrap", // Allow wrapping on mobile
        gap: "8px", // Add spacing between wrapped items
      }}
    >
      <span style={{ marginRight: "8px" }}>{initialName}</span>
      <button
        onClick={() => setIsEditing(true)}
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
    </div>
  );
};

export const GameInfoTab = ({
  gameInfo,
  isLoading,
}: {
  gameInfo: Game | null;
  isLoading: boolean;
}) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const gameFields = [
    {
      label: "Name",
      content: (
        <EditableName
          initialName={gameInfo?.name || ""}
          gameId={gameInfo?.id || ""}
        />
      ),
    },
    {
      label: "Parent Game",
      content: gameInfo?.parent_name ? (
        <Link
          to={`/play/${gameInfo.parent_name}`}
          style={{
            color: "#0084ff",
            textDecoration: "none",
          }}
        >
          {gameInfo.parent_name}
        </Link>
      ) : (
        "None"
      ),
    },
    {
      label: "Created At",
      content: formatDate(gameInfo?.created_at || ""),
    },
    {
      label: "Updated At",
      content: formatDate(gameInfo?.updated_at || ""),
    },
    {
      label: "Plays",
      content: gameInfo?.plays,
    },
  ];

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "1rem" }}>
      {isLoading ? (
        <div style={{ textAlign: "center", color: "#888", marginTop: "2rem" }}>
          Loading game information...
        </div>
      ) : gameInfo ? (
        <div>
          <h2>Game Information</h2>
          <div style={{ marginTop: "1rem" }}>
            {gameFields.map(({ label, content }) => (
              <div
                key={label}
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
                  {label}:
                </div>
                <div>{content}</div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div style={{ textAlign: "center", color: "#888", marginTop: "2rem" }}>
          Failed to load game information
        </div>
      )}
    </div>
  );
};
