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

interface Transaction {
  id: string;
  user_id: string;
  email?: string;
  status: string;
  created_at: string;
  updated_at: string;
  amount: number;
  description: string;
}

interface CostStats {
  count: number;
  total: number;
  mean: number;
  p90: number;
  p75: number;
  p25: number;
  p10: number;
}

interface MessageCosts {
  [model: string]: CostStats;
}

export const Admin = () => {
  const { loading, user } = useAuth();
  const [userStats, setUserStats] = useState<UserStats[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [messageCosts, setMessageCosts] = useState<MessageCosts>({});
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
      setTransactions(data.transactions);
      setMessageCosts(data.message_costs || {});
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
    } catch {
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
        <table
          className="user-stats-table"
          style={{
            width: "100%",
            borderCollapse: "collapse",
            border: "1px solid #ddd",
            marginBottom: "2rem",
          }}
        >
          <thead>
            <tr>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Username
              </th>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Email
              </th>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Created At
              </th>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Messages Left
              </th>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Total Messages
              </th>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Projects
              </th>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Adjust Messages Left
              </th>
            </tr>
          </thead>
          <tbody>
            {userStats.map((user) => (
              <tr key={user.id}>
                <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                  {user.username || "Anonymous"}
                </td>
                <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                  {user.email || "N/A"}
                </td>
                <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                  {formatDate(user.created_at)}
                </td>
                <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                  {user.messages_left}
                </td>
                <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                  {user.total_messages}
                </td>
                <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                  {user.n_projects}
                </td>
                <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                  <div className="message-update-controls">
                    <input
                      type="number"
                      value={updatingUserId === user.id ? messagesToAdd : 0}
                      onChange={(e) =>
                        setMessagesToAdd(parseInt(e.target.value) || 0)
                      }
                      onClick={() => {
                        // Clear the input when clicked and set the current user as updating
                        if (updatingUserId !== user.id) {
                          setUpdatingUserId(user.id);
                          setMessagesToAdd(0);
                        }
                      }}
                      placeholder="Add/remove"
                      style={{ width: "100px", marginRight: "5px" }}
                    />
                    <button
                      onClick={() => updateUserMessages(user.id)}
                      disabled={
                        updatingUserId !== null && updatingUserId !== user.id
                      }
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

      <h2>Transactions</h2>
      <div className="table-responsive">
        <table
          className="transactions-table"
          style={{
            width: "100%",
            borderCollapse: "collapse",
            border: "1px solid #ddd",
          }}
        >
          <thead>
            <tr>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Email
              </th>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Updated At
              </th>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Description
              </th>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Amount
              </th>
              <th
                style={{
                  border: "1px solid #ddd",
                  padding: "8px",
                  whiteSpace: "normal",
                  wordWrap: "break-word",
                }}
              >
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  style={{
                    border: "1px solid #ddd",
                    padding: "8px",
                    textAlign: "center",
                  }}
                >
                  No transactions found
                </td>
              </tr>
            ) : (
              transactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                    {transaction.email || "N/A"}
                  </td>
                  <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                    {formatDate(transaction.updated_at)}
                  </td>
                  <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                    {transaction.description}
                  </td>
                  <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                    {transaction.amount}
                  </td>
                  <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                    {transaction.status}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <h2>Message Cost Statistics</h2>
      <div className="table-responsive">
        <table
          className="cost-stats-table"
          style={{
            width: "100%",
            borderCollapse: "collapse",
            border: "1px solid #ddd",
          }}
        >
          <thead>
            <tr>
              {[
                "Model",
                "Count",
                "Mean Cost ($)",
                "P90 ($)",
                "P75 ($)",
                "P25 ($)",
                "P10 ($)",
                "Total ($)",
              ].map((header) => (
                <th
                  key={header}
                  style={{
                    border: "1px solid #ddd",
                    padding: "8px",
                    whiteSpace: "normal",
                    wordWrap: "break-word",
                  }}
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.keys(messageCosts).length === 0 ? (
              <tr>
                <td
                  colSpan={8}
                  style={{
                    border: "1px solid #ddd",
                    padding: "8px",
                    textAlign: "center",
                  }}
                >
                  No cost data available
                </td>
              </tr>
            ) : (
              Object.entries(messageCosts).map(([model, stats]) => (
                <tr key={model}>
                  <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                    {model}
                  </td>
                  <td style={{ border: "1px solid #ddd", padding: "8px" }}>
                    {stats.count}
                  </td>
                  {["mean", "p90", "p75", "p25", "p10", "total"].map((key) => (
                    <td
                      key={key}
                      style={{ border: "1px solid #ddd", padding: "8px" }}
                    >
                      {stats[key].toFixed(6)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
