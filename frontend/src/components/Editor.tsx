import { useParams, Navigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { GameFrame } from "./GameFrame";
import { Game } from "../types";
import { ConversationTab } from "./ConversationTab";
import { GameInfoTab } from "./GameInfoTab";

interface Message {
  id: string;
  text: string;
  sender: "user" | "assistant";
  timestamp: string;
}

type TabType = "conversation" | "info";

interface ApiResponse {
  messages: Message[];
  gameInfo: Game;
}

export const Editor = () => {
  const { gameName } = useParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>("conversation");
  const [gameInfo, setGameInfo] = useState<Game | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
        
        // Handle both formats: new format with gameInfo or old format with just messages
        if (data.messages && data.gameInfo) {
          setMessages(data.messages);
          setGameInfo(data.gameInfo);
        } else {
          // Backward compatibility with old API format
          setMessages(data);
          
          // Fetch game info separately if not included in the response
          try {
            const gameResponse = await fetch(`/api/games/${gameName}`);
            if (gameResponse.ok) {
              const gameData = await gameResponse.json();
              setGameInfo(gameData);
            }
          } catch (error) {
            console.error("Error fetching game info:", error);
          }
        }
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

  const handleSendMessage = async (inputText: string) => {
    if (!inputText.trim()) return;

    // Create a new user message
    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      sender: "user",
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

      // Handle both formats: new format with gameInfo or old format with just message
      if (data.message && data.gameInfo) {
        // Add assistant response to the chat
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: data.message,
          sender: "assistant",
          timestamp: new Date().toISOString(),
        };

        setMessages((prevMessages) => [...prevMessages, assistantMessage]);
        setGameInfo(data.gameInfo);
      } else {
        // Backward compatibility with old API format
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: data.message || "Echo: " + inputText, // Echo back if no response
          sender: "assistant",
          timestamp: new Date().toISOString(),
        };

        setMessages((prevMessages) => [...prevMessages, assistantMessage]);
      }
    } catch (error) {
      console.error("Error sending message:", error);

      // Add error message to chat
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: "Error: Could not send message. Please try again.",
        sender: "assistant",
        timestamp: new Date().toISOString(),
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
        width: "100%",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Left Column - Chat Interface and Game Info */}
      <div
        style={{
          width: "50%",
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
            gameName={gameName}
            onSendMessage={handleSendMessage}
          />
        ) : (
          <GameInfoTab
            gameInfo={gameInfo}
            isLoading={isLoading}
          />
        )}
      </div>

      {/* Right Column - Game Preview */}
      <div
        style={{
          width: "50%",
          height: "100%",
        }}
      >
        <GameFrame gameName={gameName} />
      </div>
    </div>
  );
};
