export const Info = ({ onClose }: { onClose: () => void }) => (
  <div
    onClick={onClose}
    style={{
      position: "fixed",
      top: 0,
      left: 0,
      width: "100%",
      height: "100%",
      backgroundColor: "rgba(0, 0, 0, 0.5)",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      zIndex: 1000,
    }}
  >
    <div
      onClick={(e) => e.stopPropagation()}
      style={{
        backgroundColor: "white",
        padding: "2rem",
        borderRadius: "8px",
        maxWidth: "90%",
        maxHeight: "90%",
        overflow: "auto",
        position: "relative",
      }}
    >
      <h1 style={{ marginBottom: "1.5rem", color: "#0084ff" }}>
        Welcome to Gamergate
      </h1>

      <div style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.3rem", marginBottom: "0.8rem" }}>
          Your AI Gaming Arcade
        </h2>
        <ul style={{ paddingLeft: "1.5rem", lineHeight: "1.6" }}>
          <li>Create games by chatting with an AI assistant</li>
          <li>Play and share other people's games</li>
          <li>Remix existing games to make them your own</li>
        </ul>
      </div>

      <div style={{ marginBottom: "2rem" }}>
        <p style={{ marginBottom: "0.5rem" }}>
          <strong>Login with Google to start!</strong>
        </p>
        <p style={{ fontSize: "0.9rem", color: "#666" }}>
          New users are given 10 free messages. After that, you can buy new
          messages at $5 per 100 messages.
        </p>
      </div>

      <div
        style={{
          marginTop: "2rem",
          fontSize: "0.9rem",
          color: "#666",
          borderTop: "1px solid #eee",
          paddingTop: "1rem",
        }}
      >
        <p>
          Made with curiosity by{" "}
          <a
            href="https://twitter.com/granawkins"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "#0084ff", textDecoration: "none" }}
          >
            @granawkins
          </a>
        </p>
      </div>

      <button
        onClick={onClose}
        style={{
          position: "absolute",
          top: "1rem",
          right: "1rem",
          background: "none",
          border: "none",
          fontSize: "1.5rem",
          cursor: "pointer",
        }}
      >
        ×
      </button>
    </div>
  </div>
);
