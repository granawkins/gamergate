import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Game } from "../types";

import { backendUrl } from "../utils";
import { LoadingMask } from "./LoadingMask";

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
  onSaveSuccess?: (value: string) => void;
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
          id: gameId,
          field: fieldName,
          [fieldName]: value,
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
        onSaveSuccess(value);
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
          justifyContent: "flex-end",
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
              minWidth: "120px",
              minHeight: "80px",
            }}
            autoFocus
          />
        ) : (
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={placeholder}
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
            className="primary"
            style={{
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
    <div className="info-style">
      <span>{initialValue || "No " + fieldName + " set"}</span>
      <button onClick={() => setIsEditing(true)}>Edit</button>
    </div>
  );
};

export const GameInfoTab = ({
  gameInfo,
  isLoading,
  onGameInfoUpdate,
}: {
  gameInfo: Game | null;
  isLoading: boolean;
  onGameInfoUpdate?: (updatedInfo: Partial<Game>) => void;
}) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const handleDownload = () => {
    if (!gameInfo?.name) return;

    // Create a link to the download endpoint and click it
    const downloadUrl = `${backendUrl()}/api/games/${gameInfo.name}/download`;

    // Open in a new tab/window to avoid disrupting the current page
    window.open(downloadUrl, "_blank");
  };

  // Image upload handler
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleCoverImageUpload = async () => {
    if (
      fileInputRef.current &&
      fileInputRef.current.files &&
      fileInputRef.current.files.length > 0
    ) {
      const file = fileInputRef.current.files[0];

      // Validate file is an image
      if (!file.type.startsWith("image/")) {
        alert("Please upload an image file.");
        return;
      }

      // Validate file size (max 2MB)
      if (file.size > 2 * 1024 * 1024) {
        alert("Image size should be less than 2MB.");
        return;
      }

      // Convert image to base64
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64String = e.target?.result as string;

        try {
          const response = await fetch("/api/games/update-info", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              id: gameInfo?.id,
              field: "cover_image",
              cover_image: base64String,
            }),
          });

          if (!response.ok) {
            throw new Error("Failed to upload cover image");
          }

          const data = await response.json();

          if (data.successful) {
            if (onGameInfoUpdate && gameInfo) {
              onGameInfoUpdate({ ...gameInfo, cover_image: base64String });
            }
            alert("Cover image uploaded successfully!");
          } else {
            alert("Failed to upload cover image. Please try again.");
          }
        } catch (error) {
          console.error("Error uploading cover image:", error);
          alert("Failed to upload cover image. Please try again.");
        }
      };
      reader.readAsDataURL(file);
    }
  };

  const triggerFileInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
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
          onSaveSuccess={(value) => {
            if (onGameInfoUpdate && gameInfo) {
              onGameInfoUpdate({ ...gameInfo, name: value });
            }
          }}
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
          onSaveSuccess={(value) => {
            if (onGameInfoUpdate && gameInfo) {
              onGameInfoUpdate({ ...gameInfo, description: value });
            }
          }}
        />
      ),
    },
    {
      label: "Version",
      content: gameInfo?.version || 0,
    },
    {
      label: "Cover Image",
      content: (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {gameInfo?.cover_image ? (
            <div style={{ maxWidth: "300px", marginBottom: "10px" }}>
              <img
                src={gameInfo.cover_image}
                alt="Game cover"
                style={{ width: "100%", borderRadius: "4px" }}
              />
            </div>
          ) : (
            <div style={{ color: "#888", marginBottom: "10px" }}>
              <em>No cover image set</em>
            </div>
          )}
          <div>
            <input
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              ref={fileInputRef}
              onChange={handleCoverImageUpload}
            />
            <button onClick={triggerFileInput}>Upload Cover Image</button>
          </div>
        </div>
      ),
    },
    {
      label: "Seconds Played",
      content: gameInfo?.seconds_played || "None",
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
      label: "Actions",
      content: (
        <button
          onClick={handleDownload}
          className="primary"
          disabled={!gameInfo?.name}
          title="Download game files as a ZIP archive"
        >
          <span style={{ display: "flex", alignItems: "center" }}>
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="currentColor"
              style={{ marginRight: "8px" }}
            >
              <path d="M8 12l-4-4h2.5V3h3v5H12L8 12z" />
              <path d="M14 13v1H2v-1h12z" />
            </svg>
            Download Game
          </span>
        </button>
      ),
    },
  ];

  return (
    <div style={{ position: "relative", padding: "1rem", overflowY: "auto" }}>
      {isLoading ? (
        <LoadingMask />
      ) : gameInfo ? (
        <div className="info-section">
          <h2>Game Information</h2>
          {gameFields.map(({ label, content }) => (
            <div key={label} className="info-style">
              <span>{label}:</span>
              <span>{content}</span>
            </div>
          ))}

          <div style={{ marginTop: "1rem" }}></div>
        </div>
      ) : (
        <div style={{ textAlign: "center", color: "#888", marginTop: "2rem" }}>
          Failed to load game information
        </div>
      )}
    </div>
  );
};
