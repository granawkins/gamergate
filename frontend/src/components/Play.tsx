import { useParams, Navigate } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';

export const Play = () => {
  const { gameName } = useParams();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Focus the iframe when it loads and handle resize events
  useEffect(() => {
    if (!iframeRef.current) return;
    
    // Focus the iframe
    iframeRef.current.focus();
    
    // Function to handle window resize
    const handleResize = () => {
      if (iframeRef.current && iframeRef.current.contentWindow) {
        // Send resize message to iframe
        iframeRef.current.contentWindow.postMessage('resize', '*');
      }
    };
    
    // Add resize event listener
    window.addEventListener('resize', handleResize);
    
    // Handle iframe load event
    const handleIframeLoad = () => {
      // Focus the iframe
      if (iframeRef.current) {
        iframeRef.current.focus();
      }
      
      // Trigger resize after iframe loads
      setTimeout(handleResize, 100);
    };
    
    // Add load event listener to iframe
    iframeRef.current.addEventListener('load', handleIframeLoad);
    
    // Clean up event listeners on component unmount
    return () => {
      window.removeEventListener('resize', handleResize);
      if (iframeRef.current) {
        iframeRef.current.removeEventListener('load', handleIframeLoad);
      }
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
