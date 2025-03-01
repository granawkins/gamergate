import { useState } from 'react'
import { Info } from './Info'

export const Header = () => {
  const [showInfo, setShowInfo] = useState(false)

  return (
    <header style={{ 
      borderBottom: '1px solid #ccc', 
      display: 'flex',
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
    }}>
      <a onClick={() => setShowInfo(true)} style={{ fontSize: '1.5rem', cursor: 'pointer' }}>ⓘ</a>
      <a href="/" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <h1>GAMERGATE</h1>
      </a>
      <a href="/user" style={{ fontSize: '1.5rem' }}>👤</a>
      {showInfo && <Info onClose={() => setShowInfo(false)} />}
    </header>
  )
}
