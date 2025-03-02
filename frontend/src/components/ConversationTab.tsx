import { useRef, useState } from "react";
import { Message } from "../types";

export const ConversationTab = ({
  messages,
  isLoading,
  onSendMessage,
}: {
  messages: Message[];
  isLoading: boolean;
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
                alignSelf: message.role === "user" ? "flex-end" : "flex-start",
                backgroundColor:
                  message.role === "user" ? "#0084ff" : "#e5e5ea",
                color: message.role === "user" ? "white" : "black",
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
};
