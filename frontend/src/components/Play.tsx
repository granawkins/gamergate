import { useParams, Navigate } from "react-router-dom";
import { useEffect, useRef } from "react";
import { GameFrame } from "./GameFrame";
import useAuth from "../auth/useAuth";

export const Play = () => {
  const { gameName } = useParams();
  const { user } = useAuth();
  const startTimeRef = useRef<number>(Date.now());
  const gameIdRef = useRef<string | null>(null);

  // Fetch the game info to get the game ID
  useEffect(() => {
    if (!gameName) return;

    const fetchGameId = async () => {
      try {
        const response = await fetch(`/api/games?search=${gameName}`);
        const data = await response.json();

        const game = [...data.play, ...data.templates].find(
          (g) => g.name === gameName,
        );
        if (game) {
          gameIdRef.current = game.id;
        }
      } catch (error) {
        console.error("Error fetching game info:", error);
      }
    };

    fetchGameId();
  }, [gameName]);

  // Record the play session when user leaves the page
  useEffect(() => {
    if (!gameName) return;

    const recordPlaySession = async () => {
      if (!gameIdRef.current) return;

      const endTime = Date.now();
      const sessionDuration = Math.round(
        (endTime - startTimeRef.current) / 1000,
      ); // Convert to seconds

      if (sessionDuration < 1) return; // Don't record sessions less than 1 second

      try {
        await fetch("/api/play-sessions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            game_id: gameIdRef.current,
            seconds: sessionDuration,
            user_id: user?.id || "anonymous",
          }),
        });
      } catch (error) {
        console.error("Error recording play session:", error);
      }
    };

    // Record session when component unmounts
    return () => {
      recordPlaySession();
    };
  }, [gameName, user?.id]);

  // Redirect to home if no gameName is provided
  if (!gameName) {
    return <Navigate to="/" replace />;
  }

  return <GameFrame gameName={gameName} title={gameName} />;
};
