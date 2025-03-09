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
    <div className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">User Profile</h1>

      <div className="bg-gray-100 p-4 rounded mb-4">
        {editingUsername ? (
          <form onSubmit={handleUpdateUsername} className="mb-4">
            <div className="mb-2">
              <label className="block text-sm font-medium mb-1">
                Username:
              </label>
              <input
                type="text"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                className="w-full p-2 border rounded"
                required
              />
            </div>
            {error && <p className="text-red-500 mb-2">{error}</p>}
            <div className="flex gap-2">
              <button type="submit" className="primary">
                Save
              </button>
              <button type="button" onClick={() => setEditingUsername(false)}>
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <div className="mb-4">
            <div className="flex justify-between items-center">
              <div>
                <span className="font-medium">Username:</span> {user.username}
              </div>
              <button onClick={startEditingUsername}>Edit</button>
            </div>
            {successMessage && (
              <p className="text-green-500 mt-2">{successMessage}</p>
            )}
          </div>
        )}

        <div className="mb-2">
          <span className="font-medium">Email:</span> {user.email}
        </div>

        <div className="mb-2">
          <span className="font-medium">Messages Left:</span>{" "}
          {user.messages_left}
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => (window.location.href = "/checkout")}
        >
          Buy Messages
        </button>
        <button
          onClick={logout}
        >
          Logout
        </button>
      </div>
    </div>
  );
};
