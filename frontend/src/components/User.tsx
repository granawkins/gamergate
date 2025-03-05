import useAuth from "../auth/useAuth";

export const User = () => {
  const { loading, user } = useAuth();

  const logout = () => {
    return (window.location.href = "/api/user/logout");
  };

  if (loading) {
    return null;
  } else if (!user || !user.email) {
    // Redirect to home if no user or if it's a dummy user (no email)
    return (window.location.href = "/");
  }

  return (
    <div>
      <h1>User</h1>
      {Object.entries(user).map(([key, value]) => (
        <p key={key}>
          {key}: {value}
        </p>
      ))}
      <button onClick={logout}>Logout</button>
    </div>
  );
};
