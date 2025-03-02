import { useRef, useState } from "react";
import { Message } from "../types";

export const ConversationTab = ({
  messages,
  isLoading,
  isPolling,
  onSendMessage,
}: {
  messages: Message[];
  isLoading: boolean;
  isPolling?: boolean;
  onSendMessage: (message: string) => Promise<void>;
}) => {
  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    await onSendMessage(inputText);
    setInputText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Function to render a message with appropriate styling
  const renderMessage = (message: Message) => {
    const isProcessing = message.role === "assistant" && message.status === "processing";
    
    return (
      <div
        key={message.id}
        style={{
          alignSelf: message.role === "user" ? "flex-end" : "flex-start",
          backgroundColor:
            message.role === "user" ? "#0084ff" : "#e5e5ea",
          color: message.role === "user" ? "white" : "black",
          borderRadius: "18px",
          padding: "8px 16px",
          margin: "4px 0",
          maxWidth: "80%",
          wordBreak: "break-word",
          position: "relative",
        }}
      >
        {message.text || (isProcessing ? "Thinking..." : "")}
        
        {/* Show loading indicator for processing messages */}
        {isProcessing && (
          <div
            style={{
              position: "absolute",
              bottom: "-20px",
              left: "8px",
              fontSize: "12px",
              color: "#888",
              display: "flex",
              alignItems: "center",
            }}
          >
            <div
              style={{
                display: "inline-block",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: "#888",
                marginRight: "4px",
                animation: "pulse 1s infinite ease-in-out",
              }}
            />
            <style>
              {`
                @keyframes pulse {
                  0% { opacity: 0.4; }
                  50% { opacity: 1; }
                  100% { opacity: 0.4; }
                }
              `}
            </style>
            Generating response...
          </div>
        )}
      </div>
    );
  };

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
          messages.map(renderMessage)
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
          disabled={isPolling} // Disable input while waiting for response
        />
        <button
          onClick={handleSendMessage}
          disabled={!inputText.trim() || isPolling}
          style={{
            padding: "0 16px",
            backgroundColor: "#0084ff",
            color: "white",
            border: "none",
            cursor: inputText.trim() && !isPolling ? "pointer" : "default",
            opacity: inputText.trim() && !isPolling ? 1 : 0.6,
          }}
        >
          Send
        </button>
      </div>
    </>
  );
};
