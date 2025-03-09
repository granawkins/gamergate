import React from "react";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  title?: string;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  children,
  title,
}) => {
  if (!isOpen) return null;

  return (
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
        className="modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          padding: "2rem",
          borderRadius: "8px",
          maxWidth: "90%",
          maxHeight: "90%",
          overflow: "auto",
          position: "relative",
        }}
      >
        {title && (
          <h2
            style={{ marginTop: 0, marginBottom: "1.5rem", color: "#0084ff" }}
          >
            {title}
          </h2>
        )}

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
            color: "#ccc",
          }}
        >
          ×
        </button>
      </div>
    </div>
  );
};
