import { useParams, Navigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { GameFrame } from "./GameFrame";
import { Game, Message } from "../types";
import { ConversationTab } from "./ConversationTab";
import { GameInfoTab } from "./GameInfoTab";

type TabType = "conversation" | "info";

export const Editor = () => {
  const { gameName } = useParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>("conversation");
  const [gameInfo, setGameInfo] = useState<Game | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollingIntervalRef = useRef<number | null>(null);

  // Fetch data when component mounts
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`/api/chat/${gameName}`);

        if (!response.ok) {
          throw new Error("Failed to fetch data");
        }

        const data = await response.json();
        setMessages(data.messages);
        setGameInfo(data.gameInfo);
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [gameName]);

  // Scroll to bottom of messages when new messages are added
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Poll for message updates if the last message is from the assistant and is processing
  useEffect(() => {
    // Clear any existing polling interval when component unmounts or dependencies change
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, []);

  // Start or stop polling based on the last message
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];

    // If there's no last message or it's not from the assistant or not processing, don't poll
    if (
      !lastMessage ||
      lastMessage.role !== "assistant" ||
      lastMessage.status !== "processing"
    ) {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
        setIsPolling(false);
      }
      return;
    }

    // Start polling if we have a processing assistant message
    if (!pollingIntervalRef.current) {
      setIsPolling(true);

      const pollMessage = async () => {
        try {
          const response = await fetch(
            `/api/chat/${gameName}/message/${lastMessage.id}`,
          );

          if (!response.ok) {
            throw new Error("Failed to fetch message update");
          }

          const data = await response.json();
          const updatedMessage = data.message;

          // If the message is no longer processing, update it and stop polling
          if (updatedMessage.status !== "processing") {
            setMessages((prevMessages) =>
              prevMessages.map((msg) =>
                msg.id === updatedMessage.id ? updatedMessage : msg,
              ),
            );

            clearInterval(pollingIntervalRef.current!);
            pollingIntervalRef.current = null;
            setIsPolling(false);
          }
        } catch (error) {
          console.error("Error polling for message update:", error);
        }
      };

      // Poll every second
      pollingIntervalRef.current = window.setInterval(pollMessage, 1000);

      // Initial poll
      pollMessage();
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [messages, gameName]);

  const handleSendMessage = async (inputText: string) => {
    if (!inputText.trim()) return;

    // Create a new user message
    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      role: "user",
      timestamp: new Date().toISOString(),
    };

    // Add user message to the chat
    setMessages((prevMessages) => [...prevMessages, userMessage]);

    try {
      // Send message to backend
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
    } catch (error) {
      console.error("Error sending message:", error);

      // Add error message to chat
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: "Error: Could not send message. Please try again.",
        role: "assistant",
        timestamp: new Date().toISOString(),
        status: "error",
      };

      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    }
  };

  // Redirect to home if no gameName is provided
  if (!gameName) {
    return <Navigate to="/" replace />;
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        width: "100%",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Left Column - Chat Interface and Game Info */}
      <div
        style={{
          width: "50%",
          maxWidth: "400px",
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid #ccc",
          height: "100%",
        }}
      >
        {/* Tabs */}
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

        {/* Tab Content */}
        {activeTab === "conversation" ? (
          <ConversationTab
            messages={messages}
            isLoading={isLoading}
            isPolling={isPolling}
            onSendMessage={handleSendMessage}
          />
        ) : (
          <GameInfoTab gameInfo={gameInfo} isLoading={isLoading} />
        )}
      </div>

      {/* Right Column - Game Preview */}
      <div
        style={{
          flexGrow: 1,
          height: "100%",
        }}
      >
        <GameFrame gameName={gameName} />
      </div>
    </div>
  );
};
