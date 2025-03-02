import { useState } from "react";
import { Info } from "./Info";
import useAuth from "../auth/useAuth";

export const Header = () => {
  const { loading, user } = useAuth();

  const [showInfo, setShowInfo] = useState(false);
  const loginWithGoogle = () => {
    window.location.href = "http://localhost:8000/api/user/login";
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
        onClick={() => setShowInfo(true)}
        style={{ fontSize: "1.5rem", cursor: "pointer" }}
      >
        ⓘ
      </a>
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
      {user ? (
        <a href="/user" style={{ fontSize: "1.5rem" }}>
          User
        </a>
      ) : loading ? (
        <p>Loading...</p>
      ) : (
        <a onClick={loginWithGoogle} style={{ fontSize: "1.5rem" }}>
          Login
        </a>
      )}
      {showInfo && <Info onClose={() => setShowInfo(false)} />}
    </header>
  );
};
