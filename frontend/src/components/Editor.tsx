import { useParams, Navigate } from "react-router-dom";
import { useCallback, useEffect, useRef, useState } from "react";
import { GameFrame } from "./GameFrame";
import { Game, Message } from "../types";
import { ConversationTab } from "./ConversationTab";
import { GameInfoTab } from "./GameInfoTab";
import useAuth from "../auth/useAuth";

type TabType = "conversation" | "info";

export const Editor = () => {
  const { gameName } = useParams();
  const { user, setUser } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>("conversation");
  const [isPortrait, setIsPortrait] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Function to fetch the latest user data
  const fetchUserData = useCallback(async () => {
    try {
      const response = await fetch("/api/user/me", {
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to fetch user data");
      }

      const data = await response.json();
      setUser(data.user);
    } catch (error) {
      console.error("Error fetching user data:", error);
    }
  }, [setUser]);

  // Conversation State
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [gameInfo, setGameInfo] = useState<Game | null>(null);

  const [frameKey, setFrameKey] = useState(0);

  // Check if we're in portrait mode (aspect ratio taller than 1:1)
  useEffect(() => {
    const checkOrientation = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        setIsPortrait(height > width);
      }
    };

    // Initial check
    checkOrientation();

    // Add resize listener
    window.addEventListener("resize", checkOrientation);

    // Cleanup
    return () => {
      window.removeEventListener("resize", checkOrientation);
    };
  }, []);

  useEffect(() => {
    const initializeConversation = async () => {
      try {
        const response = await fetch(`/api/chat/${gameName}`);
        if (!response.ok) {
          throw new Error("Failed to fetch data");
        }
        const data = await response.json();
        setMessages(data.messages);
        setGameInfo(data.gameInfo);
      } catch (error) {
        setError(error as string);
      } finally {
        setIsLoading(false);
      }
    };

    initializeConversation();
  }, [gameName]);

  // Completion Polling
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<number | null>(null);
  const pollMessage = useCallback(
    async (message_id: string) => {
      try {
        const response = await fetch(
          `/api/chat/${gameName}/message/${message_id}`,
        );

        if (!response.ok) {
          throw new Error("Failed to fetch message update");
        }

        const data = await response.json();
        const updatedMessage = data.message;
        setMessages((prevMessages) =>
          prevMessages.map((msg) =>
            msg.id === updatedMessage.id ? updatedMessage : msg,
          ),
        );
        if (
          updatedMessage.status !== "processing" &&
          pollingIntervalRef.current
        ) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          setIsPolling(false);
        }
        if (
          updatedMessage.status === "completed" &&
          !!updatedMessage.commit_sha
        ) {
          setFrameKey((prev) => prev + 1);

          // Update user data to get the latest messages_left count
          fetchUserData();
        }
      } catch (error) {
        setError(error as string);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          setIsPolling(false);
        }
      }
    },
    [gameName, fetchUserData],
  );

  const handleSendMessage = async (inputText: string) => {
    if (!inputText.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      role: "user",
      timestamp: new Date().toISOString(),
    };
    setMessages((prevMessages) => [...prevMessages, userMessage]);

    try {
      const response = await fetch(`/api/chat/${gameName}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: inputText }),
      });

      if (!response.ok) {
        throw new Error("Failed to send message");
      }

      const data = await response.json();
      setMessages((prevMessages) => [...prevMessages, data.message]);
      setGameInfo(data.gameInfo);
      const assistantMessageId = data.message.id;
      pollingIntervalRef.current = window.setInterval(
        () => pollMessage(assistantMessageId),
        1000,
      );
      setIsPolling(true);
    } catch (error) {
      setError(error as string);
    }
  };

  const handleUndo = async (message: Message) => {
    if (!message.commit_sha) return;

    // Show confirmation dialog
    const confirmed = window.confirm(
      "Are you sure you want to undo this change? This action cannot be undone.",
    );

    if (!confirmed) return;

    try {
      const response = await fetch(`/api/chat/${gameName}/undo`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message_id: message.id }),
      });

      if (!response.ok) {
        throw new Error("Failed to undo changes");
      }

      const data = await response.json();
      setMessages(data.messages);
      // Reload the iframe to show the changes
      setFrameKey((prev) => prev + 1);
    } catch (error) {
      setError(error as string);
    }
  };

  // Redirect to home if no gameName is provided
  if (!gameName) {
    return <Navigate to="/" replace />;
  }

  // Render the tabs for conversation and game info
  const renderTabs = () => (
    <div
      style={{
        display: "flex",
        borderBottom: "1px solid #ccc",
      }}
    >
      <div
        onClick={() => setActiveTab("conversation")}
        style={{
          padding: "0.75rem 1rem",
          cursor: "pointer",
          fontWeight: activeTab === "conversation" ? "bold" : "normal",
          borderBottom:
            activeTab === "conversation"
              ? "2px solid #0084ff"
              : "2px solid transparent",
          color: activeTab === "conversation" ? "#0084ff" : "inherit",
        }}
      >
        Conversation
      </div>
      <div
        onClick={() => setActiveTab("info")}
        style={{
          padding: "0.75rem 1rem",
          cursor: "pointer",
          fontWeight: activeTab === "info" ? "bold" : "normal",
          borderBottom:
            activeTab === "info"
              ? "2px solid #0084ff"
              : "2px solid transparent",
          color: activeTab === "info" ? "#0084ff" : "inherit",
        }}
      >
        Game Info
      </div>
    </div>
  );

  // Render the tab content (conversation or game info)
  const renderTabContent = () =>
    activeTab === "conversation" ? (
      <ConversationTab
        messages={messages}
        isLoading={isLoading}
        isPolling={isPolling}
        error={error}
        onSendMessage={handleSendMessage}
        onUndo={handleUndo}
        messagesLeft={user?.messages_left}
      />
    ) : (
      <GameInfoTab
        gameInfo={gameInfo}
        isLoading={isLoading}
        onGameInfoUpdate={(updatedInfo) =>
          setGameInfo((prev) => (prev ? { ...prev, ...updatedInfo } : null))
        }
      />
    );

  return (
    <div
      ref={containerRef}
      style={{
        display: "flex",
        flexDirection: isPortrait ? "column" : "row",
        width: "100%",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {isPortrait ? (
        // Portrait layout - Game on top, messages on bottom 30%
        <>
          {/* Top section - Game Preview */}
          <div
            style={{
              width: "100%",
              height: "70%",
              minHeight: "300px",
            }}
          >
            <GameFrame key={frameKey} gameName={gameName} isEditor={true} />
          </div>

          {/* Bottom section - Chat Interface and Game Info */}
          <div
            style={{
              width: "100%",
              height: "30%",
              minHeight: "300px",
              display: "flex",
              flexDirection: "column",
              borderTop: "1px solid #ccc",
            }}
          >
            {renderTabs()}
            {renderTabContent()}
          </div>
        </>
      ) : (
        // Landscape layout - Messages on left, game on right
        <>
          {/* Left Column - Chat Interface and Game Info */}
          <div
            style={{
              width: "40%",
              maxWidth: "400px",
              display: "flex",
              flexDirection: "column",
              borderRight: "1px solid #ccc",
              height: "100%",
            }}
          >
            {renderTabs()}
            {renderTabContent()}
          </div>

          {/* Right Column - Game Preview */}
          <div
            style={{
              flexGrow: 1,
              height: "100%",
            }}
          >
            <GameFrame key={frameKey} gameName={gameName} isEditor={true} />
          </div>
        </>
      )}
    </div>
  );
};
