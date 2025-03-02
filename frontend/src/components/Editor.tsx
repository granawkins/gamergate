import { useParams, Navigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { GameFrame } from "./GameFrame";
import { Game, Message } from "../types";
import { ConversationTab } from "./ConversationTab";
import { GameInfoTab } from "./GameInfoTab";
import { io, Socket } from "socket.io-client";

type TabType = "conversation" | "info";

export const Editor = () => {
  const { gameName } = useParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>("conversation");
  const [gameInfo, setGameInfo] = useState<Game | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const socketRef = useRef<Socket | null>(null);

  // Initialize Socket.IO connection
  useEffect(() => {
    // Create Socket.IO connection
    socketRef.current = io("/api/ws");

    // Set up event listeners
    socketRef.current.on("connect", () => {
      console.log("Connected to Socket.IO server");
    });

    socketRef.current.on("disconnect", () => {
      console.log("Disconnected from Socket.IO server");
    });

    // Listen for message updates (streaming)
    socketRef.current.on("message_update", (data) => {
      if (data.game_name === gameName) {
        // Update the message with the streamed text
        setMessages((prevMessages) => 
          prevMessages.map((msg) => 
            msg.id === data.message_id 
              ? { ...msg, text: data.text } 
              : msg
          )
        );
      }
    });

    // Listen for general errors
    socketRef.current.on("error", (error) => {
      console.error("Socket error:", error);
      // Only show an error message if it's not handled elsewhere
      if (!error.handled) {
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          text: `Error: ${error.message || "An unknown error occurred"}`,
          sender: "assistant",
          timestamp: new Date().toISOString(),
        };
        setMessages((prevMessages) => [...prevMessages, errorMessage]);
      }
    });

    // Clean up on unmount
    return () => {
      if (socketRef.current) {
        // Remove all listeners to avoid memory leaks
        socketRef.current.off("connect");
        socketRef.current.off("disconnect");
        socketRef.current.off("message_update");
        socketRef.current.off("error");
        socketRef.current.off("message_received");
        socketRef.current.disconnect();
      }
    };
  }, [gameName]);

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

  const handleSendMessage = async (inputText: string) => {
    if (!inputText.trim()) return;

    // Create a new user message with a temporary ID
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      text: inputText,
      sender: "user",
      timestamp: new Date().toISOString(),
    };

    // Add user message to the chat immediately for UI responsiveness
    setMessages((prevMessages) => [...prevMessages, tempUserMessage]);

    try {
      if (!socketRef.current || !socketRef.current.connected) {
        throw new Error("Socket not connected");
      }

      // Get the current user ID (assuming it's available in the gameInfo)
      const userId = gameInfo?.owner_id;
      
      if (!userId) {
        throw new Error("User ID not available");
      }

      // Send message via Socket.IO
      socketRef.current.emit('send_message', {
        game_name: gameName,
        message: inputText,
        user_id: userId
      });

      // Set up a one-time listener for the response
      socketRef.current.once('message_received', (data) => {
        // Replace the temporary user message with the actual one from the server
        setMessages((prevMessages) => 
          prevMessages.map((msg) => 
            msg.id === tempUserMessage.id ? data.user_message : msg
          )
        );
        
        // Add the initial empty assistant message
        // The actual content will be streamed via Socket.IO
        setMessages((prevMessages) => [...prevMessages, data.assistant_message]);
        
        // Update game info
        setGameInfo(data.game_info);
      });

      // Set up a one-time listener for errors
      socketRef.current.once('error', (error) => {
        console.error("Socket error:", error);
        throw new Error(error.message || "Failed to send message");
      });
      
    } catch (error) {
      console.error("Error sending message:", error);

      // Add error message to chat
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        text: `Error: ${error instanceof Error ? error.message : "Could not send message. Please try again."}`,
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
            onSendMessage={handleSendMessage}
            messagesEndRef={messagesEndRef}
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
