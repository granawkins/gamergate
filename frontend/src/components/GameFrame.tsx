import { useEffect, useRef, useState } from "react";

export const GameFrame = ({
  gameName,
  title,
}: {
  gameName: string;
  title?: string;
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (iframeRef.current) {
      iframeRef.current.focus();
    }

    // Handle window resize
    const handleResize = () => {
      if (iframeRef.current) {
        // Propagate the resize event to the iframe content
        try {
          const resizeEvent = new Event("resize");
          iframeRef.current.contentWindow?.dispatchEvent(resizeEvent);
        } catch (e) {
          // Ignore cross-origin frame access errors
          console.error(e);
        }
      }
    };

    window.addEventListener("resize", handleResize);

    // Clean up event listener on component unmount
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [gameName]);

  const captureSnapshot = () => {
    setIsCapturing(true);
    setError(null);

    try {
      if (!iframeRef.current || !iframeRef.current.contentWindow) {
        throw new Error("Cannot access iframe content");
      }

      const iframe = iframeRef.current;
      const iframeDocument =
        iframe.contentDocument || iframe.contentWindow.document;

      // Find the canvas element in the iframe
      // Most WebGL/ThreeJS games use a canvas element
      const canvas = iframeDocument.querySelector("canvas");

      if (!canvas) {
        throw new Error("No canvas element found in the game");
      }

      // Create a data URL from the canvas
      const dataUrl = canvas.toDataURL("image/png");

      // Create a download link
      const downloadLink = document.createElement("a");
      downloadLink.href = dataUrl;
      downloadLink.download = `${gameName}-snapshot-${new Date().toISOString().replace(/:/g, "-")}.png`;

      // Trigger the download
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
    } catch (err) {
      console.error("Error capturing snapshot:", err);
      setError(
        err instanceof Error ? err.message : "Unknown error capturing snapshot",
      );
    } finally {
      setIsCapturing(false);
    }
  };

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        overflow: "hidden",
        margin: 0,
        padding: 0,
      }}
    >
      <iframe
        ref={iframeRef}
        src={`/api/games/${gameName}/play`}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          border: "none",
          outline: "none",
          overflow: "hidden",
          margin: 0,
          padding: 0,
        }}
        title={title || `${gameName} preview`}
        allowFullScreen
        allow="autoplay; fullscreen; gamepad; keyboard-map; xr-spatial-tracking"
        autoFocus
        scrolling="no"
      />
      <div
        style={{
          position: "absolute",
          top: "10px",
          right: "10px",
          zIndex: 10,
        }}
      >
        <button
          onClick={captureSnapshot}
          disabled={isCapturing}
          style={{
            padding: "8px 12px",
            backgroundColor: "#0084ff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: isCapturing ? "not-allowed" : "pointer",
            fontWeight: "bold",
            opacity: isCapturing ? 0.7 : 1,
          }}
        >
          {isCapturing ? "Capturing..." : "Snapshot"}
        </button>
        {error && (
          <div
            style={{
              marginTop: "5px",
              padding: "5px",
              backgroundColor: "rgba(255, 0, 0, 0.1)",
              color: "red",
              borderRadius: "4px",
              fontSize: "12px",
              maxWidth: "200px",
            }}
          >
            {error}
          </div>
        )}
      </div>
    </div>
  );
};
