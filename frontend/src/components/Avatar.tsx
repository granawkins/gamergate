import React from "react";
import { User } from "../types";

interface AvatarProps {
  user: User;
  size?: number;
}

// Function to generate a consistent color based on username
const generateColor = (username: string): string => {
  // Simple hash function to generate a number from a string
  let hash = 0;
  for (let i = 0; i < username.length; i++) {
    hash = username.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  // Convert to a hex color
  let color = "#";
  for (let i = 0; i < 3; i++) {
    const value = (hash >> (i * 8)) & 0xFF;
    color += ("00" + value.toString(16)).substr(-2);
  }
  
  return color;
};

export const Avatar: React.FC<AvatarProps> = ({ user, size = 40 }) => {
  const firstLetter = user.username.charAt(0).toUpperCase();
  const backgroundColor = generateColor(user.username);
  
  // Log the avatar URL for debugging
  console.log("Avatar URL:", user.avatar_id);
  
  const avatarStyle: React.CSSProperties = {
    width: `${size}px`,
    height: `${size}px`,
    borderRadius: "50%",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor,
    color: "white",
    fontWeight: "bold",
    fontSize: `${size / 2}px`,
    textTransform: "uppercase",
    overflow: "hidden",
  };

  // Handle image loading error
  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    console.error("Error loading avatar image:", e);
    // Hide the broken image and show the fallback
    e.currentTarget.style.display = 'none';
    e.currentTarget.parentElement!.innerText = firstLetter;
  };

  // Create a proxied URL for the avatar if it exists
  const avatarUrl = user.avatar_id 
    ? `/api/user/avatar-proxy?url=${encodeURIComponent(user.avatar_id)}`
    : null;

  return (
    <div style={avatarStyle}>
      {avatarUrl ? (
        <img 
          src={avatarUrl} 
          alt={`${user.username}'s avatar`} 
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          onError={handleImageError}
        />
      ) : (
        firstLetter
      )}
    </div>
  );
};
