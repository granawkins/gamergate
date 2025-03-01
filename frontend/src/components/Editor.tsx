import { useParams, Navigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";

interface Message {
  id: string;
  text: string;
  sender: "user" | "system";
  timestamp: Date;
}

export const Editor = () => {
  const { gameName } = useParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Redirect to editor home if no gameName is provided
  if (!gameName) {
    return <Navigate to="/editor" replace />;
  }

  // Scroll to bottom of messages when new messages are added
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Handle iframe resize
  useEffect(() => {
    if (iframeRef.current) {
      iframeRef.current.focus();
    }

    // Handle window resize
    const handleResize = () => {
      if (iframeRef.current) {
        // Trigger a resize event for the iframe content
        const resizeEvent = new Event("resize");
        window.dispatchEvent(resizeEvent);

        // If the iframe content is accessible, propagate the resize event
        try {
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

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    // Create a new user message
    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      sender: "user",
      timestamp: new Date(),
    };

    // Add user message to the chat
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    
    // Clear input field
    setInputText("");

    try {
      // Send message to backend
      const response = await fetch(`/api/games/${gameName}/chat`, {
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

      // Add system response to the chat
      const systemMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.message || "Echo: " + inputText, // Echo back if no response
        sender: "system",
        timestamp: new Date(),
      };

      setMessages((prevMessages) => [...prevMessages, systemMessage]);
    } catch (error) {
      console.error("Error sending message:", error);
      
      // Add error message to chat
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: "Error: Could not send message. Please try again.",
        sender: "system",
        timestamp: new Date(),
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

  return (
    <div
      style={{
        display: "flex",
        width: "100%",
        height: "calc(100vh - 60px)", // Adjust based on header height
        overflow: "hidden",
      }}
    >
      {/* Left Column - Chat Interface */}
      <div
        style={{
          width: "50%",
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid #ccc",
          height: "100%",
        }}
      >
        <div
          style={{
            padding: "1rem",
            borderBottom: "1px solid #ccc",
          }}
        >
          <h2>Chat with {gameName}</h2>
        </div>

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
          {messages.length === 0 ? (
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
                  alignSelf: message.sender === "user" ? "flex-end" : "flex-start",
                  backgroundColor: message.sender === "user" ? "#0084ff" : "#e5e5ea",
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
            padding: "1rem",
            borderTop: "1px solid #ccc",
            display: "flex",
          }}
        >
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            style={{
              flex: 1,
              padding: "8px 12px",
              borderRadius: "20px",
              border: "1px solid #ccc",
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
              marginLeft: "8px",
              padding: "8px 16px",
              backgroundColor: "#0084ff",
              color: "white",
              border: "none",
              borderRadius: "20px",
              cursor: inputText.trim() ? "pointer" : "default",
              opacity: inputText.trim() ? 1 : 0.6,
            }}
          >
            Send
          </button>
        </div>
      </div>

      {/* Right Column - Game Preview */}
      <div
        style={{
          width: "50%",
          height: "100%",
          position: "relative",
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
          }}
          title={`${gameName} preview`}
          allowFullScreen
          allow="autoplay; fullscreen; gamepad; keyboard-map; xr-spatial-tracking"
          scrolling="no"
        />
      </div>
    </div>
  );
};
