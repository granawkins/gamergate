import { useState } from "react";
import useAuth from "../auth/useAuth";

export const User = () => {
  const { loading, user, setUser } = useAuth();
  const [editingUsername, setEditingUsername] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const logout = () => {
    return (window.location.href = "/api/user/logout");
  };

  const handleUpdateUsername = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMessage("");

    try {
      const response = await fetch("/api/user/update-info", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          field: "username",
          username: newUsername,
        }),
        credentials: "include",
      });

      const data = await response.json();

      if (!response.ok) {
        // Provide a more user-friendly message for the taken username case
        if (data.detail === "Username is already taken") {
          setError(
            "This username is already taken. Please choose another one.",
          );
        } else {
          setError(data.detail || "Failed to update username");
        }
        return;
      }

      // Update the user state with the new username
      if (user) {
        setUser({ ...user, username: newUsername });
      }

      setSuccessMessage("Username updated successfully!");
      setEditingUsername(false);
    } catch (err) {
      setError("An error occurred while updating username");
      console.error(err);
    }
  };

  const startEditingUsername = () => {
    if (user?.username) {
      setNewUsername(user.username);
    }
    setEditingUsername(true);
    setError("");
    setSuccessMessage("");
  };

  if (loading) {
    return null;
  } else if (!user || !user.email) {
    // Redirect to home if no user or if it's a dummy user (no email)
    return (window.location.href = "/");
  }

  return (
    <div style={{ margin: "1rem" }}>
      <h1>User Profile</h1>

      <div className="info-section">
        <div className="info-style">
          Username
          {editingUsername ? (
            <span className="info-style">
              <input
                type="text"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                required
              />
              <button
                type="submit"
                className="primary"
                onClick={handleUpdateUsername}
              >
                Save
              </button>
              <button type="button" onClick={() => setEditingUsername(false)}>
                Cancel
              </button>
            </span>
          ) : (
            <span className="info-style">
              {user.username}
              <button onClick={startEditingUsername}>Edit</button>
            </span>
          )}
        </div>
        {error && <p style={{ color: "red" }}>{error}</p>}
        {successMessage && <p style={{ color: "green" }}>{successMessage}</p>}

        <div className="info-style">
          <span>Email:</span> {user.email}
        </div>

        <div className="info-style">
          <span>Messages Left:</span>{" "}
          <span className="info-style">
            {user.messages_left}
            <button onClick={() => (window.location.href = "/checkout")}>
              Buy Messages
            </button>
          </span>
        </div>

        <div className="info-style">
          <button onClick={logout}>Logout</button>
        </div>
      </div>
    </div>
  );
};
