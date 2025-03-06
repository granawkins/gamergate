import { Avatar } from "./Avatar";
import useAuth from "../auth/useAuth";
import { backendUrl } from "../utils";

export const Header = () => {
  const { loading, user } = useAuth();

  const loginWithGoogle = () => {
    window.location.href = `${backendUrl()}/api/user/login`;
  };

  return (
    <header
      style={{
        borderBottom: "1px solid #ccc",
        display: "flex",
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "0 1rem",
      }}
    >
      <a
        href="/"
        style={{
          textDecoration: "none",
          color: "inherit",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
        }}
      >
        <h1>GAMERGATE</h1>
      </a>
      {user && user.email ? (
        <a
          href="/user"
          style={{
            display: "flex",
            alignItems: "center",
            textDecoration: "none",
          }}
        >
          <Avatar user={user} size={36} />
        </a>
      ) : loading ? (
        <p>Loading...</p>
      ) : (
        <a
          onClick={loginWithGoogle}
          style={{
            fontSize: "1.5rem",
            cursor: "pointer",
          }}
        >
          Login
        </a>
      )}
    </header>
  );
};
