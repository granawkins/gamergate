// Generic Modal component extracted from Info.tsx
export const Modal = ({
  onClose,
  children,
}: {
  onClose: () => void;
  children: React.ReactNode;
}) => (
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
      {children}
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
