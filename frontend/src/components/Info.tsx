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
      <h1>Info</h1>
      <button
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
