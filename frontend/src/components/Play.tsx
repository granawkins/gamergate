import { useParams } from 'react-router-dom';
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
  
  return (
    <div style={{ 
      width: '100%', 
      height: '100%',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {gameName ? (
        <>
          <div style={{ 
            padding: '0.5rem 1rem',
            borderBottom: '1px solid #eee'
          }}>
            <h2 style={{ margin: '0.5rem 0' }}>{gameName}</h2>
          </div>
          <div style={{ 
            flex: 1,
            position: 'relative',
            overflow: 'hidden'
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
        </>
      ) : (
        <div style={{ padding: '1rem' }}>
          <h1>Play</h1>
          <p>Select a game from the home page to play.</p>
        </div>
      )}
    </div>
  );
};
