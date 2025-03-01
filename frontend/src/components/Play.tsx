import { useParams, Navigate } from 'react-router-dom';
import { useEffect, useRef } from 'react';

export const Play = () => {
  const { gameName } = useParams();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  
  // Focus the iframe when it loads
  useEffect(() => {
    if (iframeRef.current) {
      iframeRef.current.focus();
    }
  }, [gameName]);
  
  // Redirect to home if no gameName is provided
  if (!gameName) {
    return <Navigate to="/" replace />;
  }
  
  return (
    <div style={{ 
      width: '100%', 
      height: '100%',
      position: 'relative'
    }}>
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
          outline: 'none'
        }} 
        title={gameName}
        allowFullScreen
        allow="autoplay; fullscreen; gamepad; keyboard-map; xr-spatial-tracking"
        autoFocus
      />
    </div>
  );
};
