import { useState } from "react";
import { Info } from "./Info";

export const Footer = () => {
  const [showInfo, setShowInfo] = useState(false);

  return (
    <>
      <footer
        style={{
          width: "100%",
          borderTop: "1px solid #ccc",
          padding: "1rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          position: "sticky",
          bottom: 0,
          backgroundColor: "white",
          marginTop: "auto",
        }}
      >
        <div>
          <span>
            &copy; 2025{" "}
            <a
              href="https://twitter.com/granawkins"
              target="_blank"
              rel="noopener noreferrer"
              style={{ textDecoration: "none", color: "#0084ff" }}
            >
              @granawkins
            </a>
          </span>
        </div>
        <div>
          <a
            onClick={() => setShowInfo(true)}
            style={{ fontSize: "1.5rem", cursor: "pointer" }}
          >
            ⓘ
          </a>
        </div>
      </footer>
      {showInfo && <Info onClose={() => setShowInfo(false)} />}
    </>
  );
};
