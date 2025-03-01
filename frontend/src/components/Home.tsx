export const Home = () => {
    return (
      <div>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginTop: '2rem' }}>
          <a href="/editor" style={{ 
            padding: '1rem 2rem',
            backgroundColor: '#4CAF50',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '4px'
          }}>Editor</a>
          <a href="/play" style={{ 
            padding: '1rem 2rem',
            backgroundColor: '#4CAF50',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '4px'
          }}>Play</a>
        </div>
      </div>
    )
  }
