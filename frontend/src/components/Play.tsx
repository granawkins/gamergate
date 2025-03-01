import { useParams, Navigate } from 'react-router-dom';
import { useEffect, useRef, useLayoutEffect } from 'react';

export const Play = () => {
  const { gameName } = useParams();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Handle resize events with useLayoutEffect to ensure it runs before browser paint
  useLayoutEffect(() => {
    if (!iframeRef.current) return;
    
    // Function to handle window resize
    const handleResize = () => {
      console.log('Window resized, sending message to iframe');
      if (iframeRef.current && iframeRef.current.contentWindow) {
        // Send resize message to iframe
        iframeRef.current.contentWindow.postMessage('resize', '*');
      }
    };
    
    // Add resize event listener with debounce
    let resizeTimer: number | null = null;
    const debouncedResize = () => {
      if (resizeTimer) {
        window.clearTimeout(resizeTimer);
      }
      resizeTimer = window.setTimeout(handleResize, 100);
    };
    
    window.addEventListener('resize', debouncedResize);
    
    // Initial resize
    handleResize();
    
    // Clean up event listeners on component unmount
    return () => {
      window.removeEventListener('resize', debouncedResize);
      if (resizeTimer) {
        window.clearTimeout(resizeTimer);
      }
    };
  }, []);
  
  // Handle iframe load
  useEffect(() => {
    if (!iframeRef.current) return;
    
    // Focus the iframe
    const focusIframe = () => {
      if (iframeRef.current) {
        iframeRef.current.focus();
      }
    };
    
    // Handle iframe load event
    const handleIframeLoad = () => {
      console.log('Iframe loaded');
      
      // Focus the iframe
      focusIframe();
      
      // Trigger resize after iframe loads
      setTimeout(() => {
        console.log('Sending initial resize message to iframe');
        if (iframeRef.current && iframeRef.current.contentWindow) {
          iframeRef.current.contentWindow.postMessage('resize', '*');
        }
      }, 500); // Longer timeout to ensure game is fully initialized
    };
    
    // Add load event listener to iframe
    iframeRef.current.addEventListener('load', handleIframeLoad);
    
    // Focus iframe on click anywhere in the container
    const handleContainerClick = () => {
      focusIframe();
    };
    
    if (containerRef.current) {
      containerRef.current.addEventListener('click', handleContainerClick);
    }
    
    // Clean up event listeners on component unmount
    return () => {
      if (iframeRef.current) {
        iframeRef.current.removeEventListener('load', handleIframeLoad);
      }
      if (containerRef.current) {
        containerRef.current.removeEventListener('click', handleContainerClick);
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
