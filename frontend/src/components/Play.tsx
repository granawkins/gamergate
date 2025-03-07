import { useRef, useEffect } from "react";
import { useParams, Navigate } from "react-router-dom";
import { GameFrame } from "./GameFrame";

export const Play = () => {
  const { gameName } = useParams();
  const timerRef = useRef<Date | null>(null);

  useEffect(() => {
    if (!timerRef.current) {
      timerRef.current = new Date();
    }
    return () => {
      if (timerRef.current) {
        const seconds = Math.floor(
          (new Date().getTime() - timerRef.current.getTime()) / 1000,
        );
        if (seconds < 1) {
          return;
        }
        fetch("/api/record-play-session", {
          method: "POST",
          credentials: "include",
          body: JSON.stringify({
            game_name: gameName,
            seconds: seconds,
          }),
        });
        timerRef.current = null;
      }
    };
  }, [gameName]);

  // Redirect to home if no gameName is provided
  if (!gameName) {
    return <Navigate to="/" replace />;
  }

  return <GameFrame gameName={gameName} title={gameName} />;
};
