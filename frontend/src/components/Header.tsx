import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Avatar } from "./Avatar";
import useAuth from "../auth/useAuth";
import { backendUrl } from "../utils";
import { Game } from "../types";
import { GameInfoModal } from "./GameInfoModal";

export const Header = () => {
  const { loading, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [gameInfo, setGameInfo] = useState<Game | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showGameInfo, setShowGameInfo] = useState(false);

  const isPlayScreen = location.pathname.startsWith("/play/");
  const gameName = isPlayScreen ? location.pathname.split("/")[2] : null;

  useEffect(() => {
    const fetchGameInfo = async () => {
      if (!isPlayScreen || !gameName) return;

      setIsLoading(true);
      try {
        const response = await fetch(`/api/games/${gameName}/info`);
        if (response.ok) {
          const data = await response.json();
          setGameInfo(data);
        } else {
          console.error("Failed to fetch game info");
        }
      } catch (error) {
        console.error("Error fetching game info:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchGameInfo();
  }, [isPlayScreen, gameName]);

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
        backgroundColor: "black",
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: "0.5rem",
        }}
      >
        <a
          onClick={() => navigate("/")}
          style={{
            textDecoration: "none",
            color: "inherit",
            display: "flex",
            alignItems: "center",
            cursor: "pointer",
          }}
        >
          <img
            src="/logo_full.png"
            alt="GAMERGATE"
            style={{
              height: "3rem",
              padding: "0.5rem",
            }}
          />
        </a>

        {isPlayScreen && (
          <>
            <span style={{ fontSize: "1.5rem", opacity: 0.6 }}>/</span>
            <div
              style={{
                display: "flex",
                alignItems: "center",
              }}
            >
              <h2
                style={{
                  margin: 0,
                  fontSize: "1.2rem",
                }}
              >
                {isLoading ? "Loading..." : gameInfo?.name || gameName}
              </h2>
              <button
                onClick={() => setShowGameInfo(true)}
                style={{
                  background: "none",
                  border: "none",
                  fontSize: "1.2rem",
                  cursor: "pointer",
                  marginLeft: "0.5rem",
                  display: "flex",
                  alignItems: "center",
                  padding: 0,
                }}
                title="Game Information"
              >
                ⓘ
              </button>
            </div>
          </>
        )}
      </div>

      {user && user.email ? (
        <a
          href="/user"
          style={{
            display: "flex",
            alignItems: "center",
            textDecoration: "none",
            padding: "0.5rem",
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

      {/* Game info modal */}
      <GameInfoModal
        isOpen={showGameInfo}
        onClose={() => setShowGameInfo(false)}
        game={gameInfo}
      />
    </header>
  );
};
