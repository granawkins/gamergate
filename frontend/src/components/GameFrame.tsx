import { useEffect, useRef, useState } from "react";

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
      // Check if the browser supports getDisplayMedia
      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        throw new Error("Screen capture is not supported in this browser");
      }

      // Prompt user to select a screen area to capture
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          cursor: "always",
        },
        audio: false,
      });

      // Create a video element to capture a frame from the stream
      const video = document.createElement("video");
      video.srcObject = stream;

      // Wait for the video to be loaded
      await new Promise<void>((resolve) => {
        video.onloadedmetadata = () => {
          video.play();
          resolve();
        };
      });

      // Wait a small amount of time to ensure the video is playing
      await new Promise((resolve) => setTimeout(resolve, 200));

      // Create a canvas to draw the video frame
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      // Draw the video frame to the canvas
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        throw new Error("Could not get canvas context");
      }
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Stop all tracks in the stream
      stream.getTracks().forEach((track) => track.stop());

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
          {isCapturing ? "Selecting area..." : "Snapshot"}
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
