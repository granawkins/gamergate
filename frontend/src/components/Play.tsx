import { useParams } from 'react-router-dom';

export const Play = () => {
  const { gameName } = useParams();
  
  return (
    <div>
      {gameName ? (
        <div style={{ width: '100%', height: 'calc(100vh - 150px)' }}>
          <h2>{gameName}</h2>
          <iframe 
            src={`/api/games/${gameName}/play`} 
            style={{ width: '100%', height: '100%', border: '1px solid #ccc', borderRadius: '4px' }} 
            title={gameName}
          />
        </div>
      ) : (
        <div>
          <h1>Play</h1>
          <p>Select a game from the home page to play.</p>
        </div>
      )}
    </div>
  );
};
