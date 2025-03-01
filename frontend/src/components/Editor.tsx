import { useParams, Navigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { GameFrame } from "./GameFrame";
import { Game } from "../types";

interface Message {
  id: string;
  text: string;
  sender: "user" | "assistant";
  timestamp: string;
}

type TabType = "conversation" | "info";

export const Editor = () => {
  const { gameName } = useParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>("conversation");
  const [gameInfo, setGameInfo] = useState<Game | null>(null);
  const [isLoadingGameInfo, setIsLoadingGameInfo] = useState(true);

  // Fetch existing messages when component mounts
  useEffect(() => {
    const fetchMessages = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`/api/chat/${gameName}`);

        if (!response.ok) {
          throw new Error("Failed to fetch messages");
        }

        const data = await response.json();
        setMessages(data);
      } catch (error) {
        console.error("Error fetching messages:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchMessages();
  }, [gameName]);

  // Fetch game info when component mounts
  useEffect(() => {
    const fetchGameInfo = async () => {
      try {
        setIsLoadingGameInfo(true);
        const response = await fetch(`/api/games/${gameName}`);

        if (!response.ok) {
          throw new Error("Failed to fetch game info");
        }

        const data = await response.json();
        setGameInfo(data);
      } catch (error) {
        console.error("Error fetching game info:", error);
      } finally {
        setIsLoadingGameInfo(false);
      }
    };

    fetchGameInfo();
  }, [gameName]);

  // Scroll to bottom of messages when new messages are added
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const handleSendMessage = async () => {
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

    // Clear input field
    setInputText("");

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

      // Add assistant response to the chat
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.message || "Echo: " + inputText, // Echo back if no response
        sender: "assistant",
        timestamp: new Date().toISOString(),
      };

      setMessages((prevMessages) => [...prevMessages, assistantMessage]);
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Redirect to home if no gameName is provided
  if (!gameName) {
    return <Navigate to="/" replace />;
  }

  // Render the tab content based on the active tab
  const renderTabContent = () => {
    switch (activeTab) {
      case "conversation":
        return (
          <>
            {/* Messages Container */}
            <div
              ref={chatContainerRef}
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "1rem",
                display: "flex",
                flexDirection: "column",
              }}
            >
              {isLoading ? (
                <div
                  style={{
                    textAlign: "center",
                    color: "#888",
                    marginTop: "2rem",
                  }}
                >
                  Loading messages...
                </div>
              ) : messages.length === 0 ? (
                <div
                  style={{
                    textAlign: "center",
                    color: "#888",
                    marginTop: "2rem",
                  }}
                >
                  Start a conversation to edit the game
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    style={{
                      alignSelf:
                        message.sender === "user" ? "flex-end" : "flex-start",
                      backgroundColor:
                        message.sender === "user" ? "#0084ff" : "#e5e5ea",
                      color: message.sender === "user" ? "white" : "black",
                      borderRadius: "18px",
                      padding: "8px 16px",
                      margin: "4px 0",
                      maxWidth: "80%",
                      wordBreak: "break-word",
                    }}
                  >
                    {message.text}
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div
              style={{
                display: "flex",
                borderTop: "1px solid #ccc",
              }}
            >
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a message..."
                style={{
                  flex: 1,
                  padding: "8px",
                  border: "none",
                  borderRight: "1px solid #ccc",
                  resize: "none",
                  minHeight: "40px",
                  maxHeight: "120px",
                  outline: "none",
                }}
                rows={1}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputText.trim()}
                style={{
                  padding: "0 16px",
                  backgroundColor: "#0084ff",
                  color: "white",
                  border: "none",
                  cursor: inputText.trim() ? "pointer" : "default",
                  opacity: inputText.trim() ? 1 : 0.6,
                }}
              >
                Send
              </button>
            </div>
          </>
        );
      case "info":
        return (
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "1rem",
            }}
          >
            {isLoadingGameInfo ? (
              <div
                style={{
                  textAlign: "center",
                  color: "#888",
                  marginTop: "2rem",
                }}
              >
                Loading game information...
              </div>
            ) : gameInfo ? (
              <div>
                <h2>Game Information</h2>
                <div style={{ marginTop: "1rem" }}>
                  {Object.entries(gameInfo).map(([key, value]) => (
                    <div
                      key={key}
                      style={{
                        display: "flex",
                        padding: "0.5rem 0",
                        borderBottom: "1px solid #eee",
                      }}
                    >
                      <div
                        style={{
                          fontWeight: "bold",
                          width: "120px",
                          flexShrink: 0,
                        }}
                      >
                        {key}:
                      </div>
                      <div>{String(value)}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div
                style={{
                  textAlign: "center",
                  color: "#888",
                  marginTop: "2rem",
                }}
              >
                Failed to load game information
              </div>
            )}
          </div>
        );
      default:
        return null;
    }
  };

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
        {renderTabContent()}
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
