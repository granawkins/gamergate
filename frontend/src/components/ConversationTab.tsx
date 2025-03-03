import { useEffect, useRef, useState } from "react";
import { Message as MessageType } from "../types";

// Message component for rendering individual messages
const Message = ({ 
  message, 
  onUndo 
}: { 
  message: MessageType;
  onUndo?: (message: MessageType) => void;
}) => {
  const isProcessing =
    message.role === "assistant" && message.status === "processing";
  
  const showUndoButton = 
    message.role === "assistant" && 
    message.status === "completed" && 
    message.commit_sha;

  return (
    <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
      <div
        style={{
          alignSelf: message.role === "user" ? "flex-end" : "flex-start",
          backgroundColor: message.role === "user" ? "#0084ff" : "#e5e5ea",
          color: message.role === "user" ? "white" : "black",
          borderRadius: "18px",
          padding: "8px 16px",
          margin: "4px 0",
          maxWidth: "80%",
          wordBreak: "break-word",
          whiteSpace: "pre-wrap",
        }}
      >
        {message.status === "error"
          ? "Error, try again later"
          : message.text || (isProcessing ? "..." : "")}
      </div>
      
      {showUndoButton && onUndo && (
        <button
          onClick={() => onUndo(message)}
          style={{
            marginLeft: "8px",
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "18px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "4px",
            borderRadius: "50%",
            color: "#666",
          }}
          title="Undo this change"
        >
          ↩️
        </button>
      )}
    </div>
  );
};

const InfoMessage = ({ text }: { text: string }) => (
  <div
    style={{
      textAlign: "center",
      color: "#888",
      marginTop: "2rem",
    }}
  >
    {text}
  </div>
);

export const ConversationTab = ({
  messages,
  isLoading,
  isPolling,
  error,
  onSendMessage,
  onUndo,
}: {
  messages: MessageType[];
  isLoading: boolean;
  isPolling?: boolean;
  error?: string;
  onSendMessage: (message: string) => Promise<void>;
  onUndo?: (message: MessageType) => Promise<void>;
}) => {
  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const textDisabled = isLoading || isPolling || !!error;
  const sendDisabled = !inputText.trim() || textDisabled;

  return (
    <>
      {/* Messages Container */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "1rem",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {isLoading ? (
          <InfoMessage text="Loading messages..." />
        ) : messages.length === 0 ? (
          <InfoMessage text="Start a conversation to edit the game" />
        ) : (
          messages.map((message) => (
            <Message 
              key={message.id} 
              message={message} 
              onUndo={onUndo}
            />
          ))
        )}
        {error && (
          <InfoMessage text={`${error}. Please refresh or try again later.`} />
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
            opacity: textDisabled ? 0.6 : 1,
          }}
          rows={1}
          disabled={textDisabled} // Disable input while waiting for response
        />
        <button
          onClick={handleSendMessage}
          disabled={sendDisabled}
          style={{
            padding: "0 16px",
            backgroundColor: "#0084ff",
            color: "white",
            border: "none",
            cursor: sendDisabled ? "default" : "pointer",
            opacity: sendDisabled ? 0.6 : 1,
          }}
        >
          Send
        </button>
      </div>
    </>
  );
};
