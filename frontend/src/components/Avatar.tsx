import React from "react";
import { User } from "../types";

interface AvatarProps {
  user: User;
  size?: number;
}

// Fixed dark purple color as requested
const AVATAR_BACKGROUND_COLOR = "#4A148C";

export const Avatar: React.FC<AvatarProps> = ({ user, size = 40 }) => {
  const firstLetter = user.username.charAt(0).toUpperCase();

  const avatarStyle: React.CSSProperties = {
    width: `${size}px`,
    height: `${size}px`,
    borderRadius: "50%",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: AVATAR_BACKGROUND_COLOR,
    color: "white",
    fontWeight: "bold",
    fontSize: `${size / 2}px`,
    textTransform: "uppercase",
    overflow: "hidden",
  };

  // Handle image loading error
  const handleImageError = (
    e: React.SyntheticEvent<HTMLImageElement, Event>,
  ) => {
    console.error("Error loading avatar image:", e);
    // Hide the broken image and show the fallback
    e.currentTarget.style.display = "none";
    e.currentTarget.parentElement!.innerText = firstLetter;
  };

  // Use the avatar_id directly if available
  // This approach relies on the browser's ability to handle cross-origin requests
  // If this doesn't work, we can fall back to the proxy approach
  return (
    <div style={avatarStyle}>
      {user.avatar_id ? (
        <img
          src={user.avatar_id}
          alt={`${user.username}'s avatar`}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          onError={handleImageError}
          referrerPolicy="no-referrer"
          crossOrigin="anonymous"
        />
      ) : (
        firstLetter
      )}
    </div>
  );
};
