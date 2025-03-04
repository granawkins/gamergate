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

    // Handle messages from the iframe
    const handleMessage = (event: MessageEvent) => {
      // Make sure the message is from our iframe
      if (
        iframeRef.current &&
        event.source === iframeRef.current.contentWindow
      ) {
        if (event.data.type === "screenshotResult") {
          // We got a successful screenshot
          const dataUrl = event.data.dataUrl;

          // Create a download link
          const downloadLink = document.createElement("a");
          downloadLink.href = dataUrl;
          downloadLink.download = `${gameName}-snapshot-${new Date().toISOString().replace(/:/g, "-")}.png`;

          // Trigger the download
          document.body.appendChild(downloadLink);
          downloadLink.click();
          document.body.removeChild(downloadLink);

          setIsCapturing(false);
        } else if (event.data.type === "screenshotError") {
          // We got an error
          setError(event.data.error || "Unknown error capturing screenshot");
          setIsCapturing(false);
        }
      }
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("message", handleMessage);

    // Clean up event listeners on component unmount
    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("message", handleMessage);
    };
  }, [gameName]);

  const captureSnapshot = () => {
    setIsCapturing(true);
    setError(null);

    try {
      if (!iframeRef.current || !iframeRef.current.contentWindow) {
        throw new Error("Cannot access iframe content");
      }

      // Send a message to the iframe to request a screenshot
      iframeRef.current.contentWindow.postMessage(
        {
          type: "takeScreenshot",
        },
        "*",
      );

      // The response will be handled by the message event listener
    } catch (err) {
      console.error("Error requesting snapshot:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Unknown error requesting snapshot",
      );
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
