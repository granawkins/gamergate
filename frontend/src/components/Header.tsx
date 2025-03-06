import { useState } from "react";
import { Avatar } from "./Avatar";
import useAuth from "../auth/useAuth";
import { backendUrl } from "../utils";
import { GameInfoModal } from "./GameInfoModal";
import { Game } from "../types";

interface HeaderProps {
  gameName?: string;
}

export const Header = ({ gameName }: HeaderProps) => {
  const { loading, user } = useAuth();
  const [showGameInfo, setShowGameInfo] = useState(false);

  const loginWithGoogle = () => {
    window.location.href = `${backendUrl()}/api/user/login`;
  };

  const handleCloneGame = (game: Game) => {
    // Redirect to clone endpoint
    window.location.href = `/api/games/${game.name}/clone`;
  };

  return (
    <>
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
        <div style={{ display: "flex", alignItems: "center" }}>
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

          {gameName && (
            <span
              onClick={() => setShowGameInfo(true)}
              style={{
                marginLeft: "10px",
                color: "#555",
                cursor: "pointer",
                fontSize: "1.2rem",
              }}
            >
              / {gameName}
            </span>
          )}
        </div>

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

      {/* Game Info Modal */}
      {showGameInfo && gameName && (
        <GameInfoModal
          gameName={gameName}
          onClose={() => setShowGameInfo(false)}
          onClone={handleCloneGame}
        />
      )}
    </>
  );
};
