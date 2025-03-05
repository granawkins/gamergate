import { useParams, Navigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { GameFrame } from "./GameFrame";
import useAuth from "../auth/useAuth";

// Constants for play session tracking
const IDLE_TIMEOUT_MS = 60000; // 1 minute of inactivity is considered idle
const ACTIVITY_EVENTS = [
  "mousedown",
  "mousemove",
  "keypress",
  "scroll",
  "touchstart",
  "click",
];

export const Play = () => {
  const { gameName } = useParams();
  const { user } = useAuth();

  // Play session tracking
  const [gameId, setGameId] = useState<string | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const activeTimeRef = useRef<number>(0);
  const lastActivityRef = useRef<number>(Date.now());
  const isActiveRef = useRef<boolean>(true);
  const idleTimeoutRef = useRef<number | null>(null);
  const visibilityChangeRef = useRef<boolean>(false);

  // Redirect to home if no gameName is provided
  if (!gameName) {
    return <Navigate to="/" replace />;
  }

  // Find game ID from name
  useEffect(() => {
    const fetchGameId = async () => {
      try {
        const response = await fetch("/api/games");
        if (response.ok) {
          const games = await response.json();
          const game = games.find(
            (g: { name: string; id: string }) => g.name === gameName,
          );
          if (game) {
            setGameId(game.id);
          }
        }
      } catch (error) {
        console.error("Error fetching game ID:", error);
      }
    };

    fetchGameId();
  }, [gameName]);

  // Function to record play session
  const recordPlaySession = async (seconds: number) => {
    if (!user || !gameId || seconds <= 0) return;

    try {
      await fetch("/api/play-sessions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          game_id: gameId,
          seconds_played: Math.round(seconds),
        }),
      });
    } catch (error) {
      console.error("Error recording play session:", error);
    }
  };

  // Handle user activity
  const handleActivity = () => {
    const now = Date.now();

    // If we were idle and now active, add the idle time to the active time
    if (!isActiveRef.current) {
      isActiveRef.current = true;
    }

    lastActivityRef.current = now;

    // Clear any existing timeout
    if (idleTimeoutRef.current) {
      window.clearTimeout(idleTimeoutRef.current);
    }

    // Set a new timeout
    idleTimeoutRef.current = window.setTimeout(() => {
      isActiveRef.current = false;
    }, IDLE_TIMEOUT_MS);
  };

  // Handle visibility change (tab switching)
  const handleVisibilityChange = () => {
    visibilityChangeRef.current = document.hidden;

    if (document.hidden) {
      // User switched away from the tab
      const now = Date.now();
      const activeTime =
        now - Math.max(startTimeRef.current, lastActivityRef.current);
      if (isActiveRef.current && activeTime > 0) {
        activeTimeRef.current += activeTime;
      }
    } else {
      // User returned to the tab
      lastActivityRef.current = Date.now();
      isActiveRef.current = true;
    }
  };

  // Setup activity tracking
  useEffect(() => {
    // Reset tracking variables
    startTimeRef.current = Date.now();
    activeTimeRef.current = 0;
    lastActivityRef.current = Date.now();
    isActiveRef.current = true;

    // Add event listeners for activity tracking
    ACTIVITY_EVENTS.forEach((event) => {
      window.addEventListener(event, handleActivity);
    });

    // Add visibility change listener
    document.addEventListener("visibilitychange", handleVisibilityChange);

    // Set initial idle timeout
    idleTimeoutRef.current = window.setTimeout(() => {
      isActiveRef.current = false;
    }, IDLE_TIMEOUT_MS);

    // Record session on unmount
    return () => {
      // Calculate final active time
      const now = Date.now();
      let finalActiveTime = activeTimeRef.current;

      // Add time since last activity if still active
      if (isActiveRef.current && !visibilityChangeRef.current) {
        const additionalTime =
          now - Math.max(startTimeRef.current, lastActivityRef.current);
        if (additionalTime > 0) {
          finalActiveTime += additionalTime;
        }
      }

      // Convert to seconds
      const activeSeconds = finalActiveTime / 1000;

      // Record the session
      recordPlaySession(activeSeconds);

      // Clean up event listeners
      ACTIVITY_EVENTS.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
      document.removeEventListener("visibilitychange", handleVisibilityChange);

      // Clear timeout
      if (idleTimeoutRef.current) {
        window.clearTimeout(idleTimeoutRef.current);
      }
    };
  }, [gameName, gameId, user, recordPlaySession]);

  return <GameFrame gameName={gameName} title={gameName} />;
};
