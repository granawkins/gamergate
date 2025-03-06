import { useState, useEffect } from "react";
import useAuth from "../auth/useAuth";

interface UserStats {
  id: string;
  username?: string;
  email?: string;
  created_at: string;
  messages_left: number;
  total_messages: number;
  n_projects: number;
}

export const Admin = () => {
  const { loading, user } = useAuth();
  const [userStats, setUserStats] = useState<UserStats[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);
  const [messagesToAdd, setMessagesToAdd] = useState<number>(0);

  useEffect(() => {
    // If not loading and user is not admin, redirect to home
    if (!loading) {
      if (!user || !user.admin) {
        window.location.href = "/";
      } else {
        fetchUserStats();
      }
    }
  }, [loading, user]);

  const fetchUserStats = async () => {
    try {
      setIsLoading(true);
      const response = await fetch("/api/admin/stats");

      if (!response.ok) {
        throw new Error("Failed to fetch user statistics");
      }

      const data = await response.json();
      setUserStats(data.users);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      console.error("Error fetching user stats:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const updateUserMessages = async (userId: string) => {
    try {
      setUpdatingUserId(userId);
      const response = await fetch("/api/admin/update-messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
          messages_to_add: messagesToAdd,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to update user messages");
      }

      // Refresh user stats after update
      await fetchUserStats();
      setMessagesToAdd(0);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      console.error("Error updating user messages:", err);
    } finally {
      setUpdatingUserId(null);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch (e) {
      return dateString;
    }
  };

  if (loading || isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return (
      <div className="error-message">
        <h2>Error</h2>
        <p>{error}</p>
        <button onClick={fetchUserStats}>Try Again</button>
      </div>
    );
  }

  return (
    <div className="admin-container">
      <h1>Admin Dashboard</h1>
      <h2>User Statistics</h2>

      <div className="table-responsive">
        <table className="user-stats-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Created At</th>
              <th>Messages Left</th>
              <th>Total Messages</th>
              <th>Projects</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {userStats.map((user) => (
              <tr key={user.id}>
                <td>{user.username || "Anonymous"}</td>
                <td>{user.email || "N/A"}</td>
                <td>{formatDate(user.created_at)}</td>
                <td>{user.messages_left}</td>
                <td>{user.total_messages}</td>
                <td>{user.n_projects}</td>
                <td>
                  <div className="message-update-controls">
                    <input
                      type="number"
                      value={updatingUserId === user.id ? messagesToAdd : 0}
                      onChange={(e) =>
                        setMessagesToAdd(parseInt(e.target.value) || 0)
                      }
                      placeholder="Messages to add"
                    />
                    <button
                      onClick={() => updateUserMessages(user.id)}
                      disabled={updatingUserId !== null}
                    >
                      {updatingUserId === user.id ? "Updating..." : "Update"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Admin;
