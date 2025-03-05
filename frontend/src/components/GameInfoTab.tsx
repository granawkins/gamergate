import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Game } from "../types";

// EditableField component for handling field editing functionality
const EditableField = ({
  initialValue,
  gameId,
  fieldName,
  fieldType = "text",
  placeholder = "",
  validation = () => ({ valid: true, message: "" }),
  onSaveSuccess = () => {},
}: {
  initialValue: string;
  gameId: string;
  fieldName: "name" | "description";
  fieldType?: string;
  placeholder?: string;
  validation?: (value: string) => { valid: boolean; message: string };
  onSaveSuccess?: () => void;
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(initialValue);
  const [isUpdating, setIsUpdating] = useState(false);

  // Update value when initialValue changes
  useEffect(() => {
    setValue(initialValue);
  }, [initialValue]);

  const handleCancel = () => {
    // Reset to original value and exit edit mode
    setValue(initialValue);
    setIsEditing(false);
  };

  const handleSave = async () => {
    // Validate the value
    const validationResult = validation(value);
    if (!validationResult.valid) {
      alert(validationResult.message);
      return;
    }

    // Don't save if value hasn't changed
    if (value === initialValue) {
      setIsEditing(false);
      return;
    }

    // Update the field
    setIsUpdating(true);
    try {
      const response = await fetch("/api/games/update-info", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          [fieldName]: value,
          current_game_id: gameId,
          field: fieldName,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to update game ${fieldName}`);
      }

      const data = await response.json();

      // Handle the response
      if (data.successful === false) {
        if (fieldName === "name") {
          alert(
            `The name "${value}" is already taken. Please choose a different name.`,
          );
        } else {
          alert(`Failed to update ${fieldName}. Please try again.`);
        }
        return;
      }

      // If the update was successful
      if (data.successful === true) {
        setIsEditing(false);

        // Special handling for name field - redirect to new URL
        if (fieldName === "name") {
          const currentPath = window.location.pathname;
          const pathParts = currentPath.split("/");

          // Replace the game name in the URL
          if (pathParts.length >= 3 && pathParts[1] === "editor") {
            pathParts[2] = value;
            const newPath = pathParts.join("/");
            window.location.href = window.location.origin + newPath;
            return;
          }
        }

        // Call the success callback
        onSaveSuccess();
      }

      // Handle other cases
      setIsEditing(false);
    } catch (error) {
      console.error(`Error updating game ${fieldName}:`, error);
      alert(`Failed to update the game ${fieldName}. Please try again.`);
    } finally {
      setIsUpdating(false);
    }
  };

  if (isEditing) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: fieldType === "textarea" ? "flex-start" : "center",
          flex: 1,
          flexWrap: "wrap", // Allow wrapping on mobile
          gap: "8px", // Add spacing between wrapped items
        }}
      >
        {fieldType === "textarea" ? (
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={placeholder}
            style={{
              padding: "4px 8px",
              border: "1px solid #ccc",
              borderRadius: "4px",
              flexGrow: 1,
              minWidth: "120px",
              minHeight: "80px",
              marginRight: "8px",
              fontFamily: "inherit",
              fontSize: "inherit",
            }}
            autoFocus
          />
        ) : (
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={placeholder}
            style={{
              padding: "4px 8px",
              border: "1px solid #ccc",
              borderRadius: "4px",
              flexGrow: 1,
              minWidth: "120px",
              marginRight: "8px",
            }}
            autoFocus
          />
        )}
        <div
          style={{
            display: "flex",
            gap: "8px",
            marginTop: fieldType === "textarea" ? "8px" : "0",
          }}
        >
          <button
            onClick={handleSave}
            disabled={isUpdating}
            style={{
              padding: "4px 8px",
              backgroundColor: "#0084ff",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: isUpdating ? "default" : "pointer",
              opacity: isUpdating ? 0.7 : 1,
            }}
          >
            {isUpdating ? "Saving..." : "Save"}
          </button>
          <button
            onClick={handleCancel}
            disabled={isUpdating}
            style={{
              padding: "4px 8px",
              backgroundColor: "#f0f0f0",
              border: "1px solid #ccc",
              borderRadius: "4px",
              cursor: isUpdating ? "default" : "pointer",
              opacity: isUpdating ? 0.7 : 1,
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
      <span style={{ marginRight: "8px" }}>
        {initialValue || <em style={{ color: "#888" }}>No {fieldName} set</em>}
      </span>
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
        <EditableField
          initialValue={gameInfo?.name || ""}
          gameId={gameInfo?.id || ""}
          fieldName="name"
          validation={(value) => ({
            valid: !!value.trim(),
            message: "Game name cannot be empty",
          })}
        />
      ),
    },
    {
      label: "Description",
      content: (
        <EditableField
          initialValue={gameInfo?.description || ""}
          gameId={gameInfo?.id || ""}
          fieldName="description"
          fieldType="textarea"
          placeholder="Add a description for your game..."
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
                  flexDirection: label === "Description" ? "column" : "row",
                }}
              >
                <div
                  style={{
                    fontWeight: "bold",
                    width: label === "Description" ? "auto" : "120px",
                    flexShrink: 0,
                    marginBottom: label === "Description" ? "8px" : "0",
                  }}
                >
                  {label}:
                </div>
                <div style={{ flex: 1 }}>{content}</div>
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
