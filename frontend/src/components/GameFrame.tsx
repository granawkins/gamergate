import { useEffect, useRef, useState } from "react";
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

export const GameFrame = ({
  gameName,
  title,
  isEditor = false,
}: {
  gameName: string;
  title?: string;
  isEditor?: boolean;
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const { user } = useAuth();
  
  // Play session tracking
  const [gameId, setGameId] = useState<string | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const activeTimeRef = useRef<number>(0);
  const lastActivityRef = useRef<number>(Date.now());
  const isActiveRef = useRef<boolean>(true);
  const idleTimeoutRef = useRef<number | null>(null);
  const visibilityChangeRef = useRef<boolean>(false);

  // Find game ID from name
  useEffect(() => {
    const fetchGameId = async () => {
      try {
        const response = await fetch("/api/games");
        if (response.ok) {
          const games = await response.json();
          const game = games.find((g: any) => g.name === gameName);
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
    if (!user || !gameId || seconds <= 0 || isEditor) return;

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
      const activeTime = now - Math.max(startTimeRef.current, lastActivityRef.current);
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
    if (isEditor) return; // Don't track play time in editor mode
    
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
        const additionalTime = now - Math.max(startTimeRef.current, lastActivityRef.current);
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
  }, [gameName, gameId, user, isEditor]);

  useEffect(() => {
    if (iframeRef.current) {
      iframeRef.current.focus();
    }

    // Handle window resize
    const handleResize = () => {
      if (iframeRef.current) {
        // Propagate the resize event to the iframe content
        try {
          const resizeEvent = new Event("resize");
          iframeRef.current.contentWindow?.dispatchEvent(resizeEvent);
        } catch (e) {
          // Ignore cross-origin frame access errors
          console.error(e);
        }
      }
    };

    window.addEventListener("resize", handleResize);

    // Clean up event listener on component unmount
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [gameName]);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        overflow: "hidden",
        margin: 0,
        padding: 0,
      }}
    >
      <iframe
        ref={iframeRef}
        src={`/api/games/${gameName}/play`}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          border: "none",
          outline: "none",
          overflow: "hidden",
          margin: 0,
          padding: 0,
        }}
        title={title || `${gameName} preview`}
        allowFullScreen
        allow="autoplay; fullscreen; gamepad; keyboard-map; xr-spatial-tracking"
        autoFocus
        scrolling="no"
      />
    </div>
  );
};
