import { useEffect, useRef, useState } from "react";
import { Message as MessageType } from "../types";
import { LoadingMask } from "./LoadingMask";

// Message component for rendering individual messages
const Message = ({
  message,
  onUndo,
  isLastAssistantMessage,
}: {
  message: MessageType;
  onUndo?: (message: MessageType) => void;
  isLastAssistantMessage?: boolean;
}) => {
  const isProcessing =
    message.role === "assistant" && message.status === "processing";

  const showUndoButton =
    isLastAssistantMessage &&
    message.role === "assistant" &&
    message.status === "completed" &&
    message.commit_sha;

  return (
    <div
      style={{ position: "relative", display: "flex", alignItems: "center" }}
    >
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
        {message.text || (isProcessing ? "..." : "")}
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
  messagesLeft,
}: {
  messages: MessageType[];
  isLoading: boolean;
  isPolling?: boolean;
  error?: string;
  onSendMessage: (message: string, model: string) => Promise<void>;
  onUndo?: (message: MessageType) => Promise<void>;
  messagesLeft?: number;
}) => {
  const [inputText, setInputText] = useState("");
  const [selectedModel, setSelectedModel] = useState("o3-mini");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const models = [
    { id: "o3-mini", name: "OpenAI o3-mini" },
    { id: "gpt-4o", name: "GPT-4o" },
    { id: "claude-3-5-sonnet-20241022", name: "Claude 3.5 New" },
  ];

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    await onSendMessage(inputText, selectedModel);
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
          messages.map((message, index) => {
            // Find the last assistant message with a commit_sha
            const lastAssistantMessageIndex = [...messages]
              .reverse()
              .findIndex(
                (msg) =>
                  msg.role === "assistant" &&
                  msg.status === "completed" &&
                  msg.commit_sha,
              );

            const isLastAssistantMessage =
              lastAssistantMessageIndex !== -1 &&
              index === messages.length - 1 - lastAssistantMessageIndex;

            return (
              <Message
                key={message.id}
                message={message}
                onUndo={isLastAssistantMessage ? onUndo : undefined}
                isLastAssistantMessage={isLastAssistantMessage}
              />
            );
          })
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
          flexDirection: "column",
          borderTop: "1px solid #ccc",
        }}
      >
        <div
          style={{
            display: "flex",
            position: "relative", // Added position relative for absolute positioning of LoadingMask
          }}
        >
          {isPolling && <LoadingMask />} {/* Show loading mask while polling */}
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

        {/* Model selector and messages left counter */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: "12px",
            color: "#666",
            padding: "4px 8px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center" }}>
            <label htmlFor="model-select" style={{ marginRight: "8px" }}>
              Model:
            </label>
            <select
              id="model-select"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{
                padding: "2px 4px",
                fontSize: "12px",
                border: "1px solid #ccc",
                borderRadius: "4px",
              }}
              disabled={textDisabled}
            >
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>

          {messagesLeft !== undefined && (
            <div>Messages left: {messagesLeft}</div>
          )}
        </div>
      </div>
    </>
  );
};
