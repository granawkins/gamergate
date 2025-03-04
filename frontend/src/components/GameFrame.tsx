import { useEffect, useRef, useState } from "react";
import html2canvas from "html2canvas";

export const GameFrame = ({
  gameName,
  title,
}: {
  gameName: string;
  title?: string;
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
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

    // Clean up event listeners on component unmount
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [gameName]);

  const captureSnapshot = async () => {
    setIsCapturing(true);
    setError(null);

    try {
      if (!iframeRef.current) {
        throw new Error("Cannot access iframe");
      }

      // Wait for iframe to load completely
      if (iframeRef.current.contentDocument?.readyState !== "complete") {
        await new Promise<void>((resolve) => {
          const onLoad = () => {
            iframeRef.current?.removeEventListener("load", onLoad);
            resolve();
          };
          iframeRef.current.addEventListener("load", onLoad);
        });
      }

      // Use html2canvas to capture the iframe
      const canvas = await html2canvas(iframeRef.current, {
        useCORS: true,
        allowTaint: true,
        logging: false,
        // Attempt to capture WebGL content
        onclone: (documentClone) => {
          // This function runs before the screenshot is taken
          // We can use it to prepare the cloned document
          console.log("Preparing document for screenshot");
        },
      });

      // Convert canvas to data URL
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
      ref={containerRef}
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
