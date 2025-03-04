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

  return (
    <div style={avatarStyle}>
      {user.avatar_id ? (
        <img 
          src={user.avatar_id} 
          alt={`${user.username}'s avatar`} 
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        firstLetter
      )}
    </div>
  );
};
