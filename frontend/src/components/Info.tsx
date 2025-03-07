import { Modal } from "./Modal";

export const Info = ({ onClose }: { onClose: () => void }) => (
  <Modal isOpen={true} onClose={onClose} title="Welcome to Gamergate">
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
  </Modal>
);
