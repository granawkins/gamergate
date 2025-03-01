import { useParams, Navigate } from 'react-router-dom';
import { useEffect, useRef } from 'react';

export const Play = () => {
  const { gameName } = useParams();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (iframeRef.current) {
      iframeRef.current.focus();
    }

    // Handle window resize
    const handleResize = () => {
      if (iframeRef.current) {
        // Trigger a resize event for the iframe content
        const resizeEvent = new Event('resize');
        window.dispatchEvent(resizeEvent);
        
        // If the iframe content is accessible, propagate the resize event
        try {
          iframeRef.current.contentWindow?.dispatchEvent(resizeEvent);
        } catch (e) {
          // Ignore cross-origin frame access errors
        }
      }
    };

    window.addEventListener('resize', handleResize);
    
    // Clean up event listener on component unmount
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [gameName]);
  
  // Redirect to home if no gameName is provided
  if (!gameName) {
    return <Navigate to="/" replace />;
  }
  
  return (
    <div 
      ref={containerRef}
      style={{ 
        width: '100%', 
        height: '100%',
        position: 'relative',
        overflow: 'hidden', // Prevent scrollbars
        margin: 0,
        padding: 0
      }}
    >
      <iframe 
        ref={iframeRef}
        src={`/api/games/${gameName}/play`} 
        style={{ 
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%', 
          height: '100%', 
          border: 'none',
          outline: 'none',
          overflow: 'hidden', // Prevent scrollbars
          margin: 0,
          padding: 0
        }} 
        title={gameName}
        allowFullScreen
        allow="autoplay; fullscreen; gamepad; keyboard-map; xr-spatial-tracking"
        autoFocus
        scrolling="no" // Disable scrolling
      />
    </div>
  );
};
