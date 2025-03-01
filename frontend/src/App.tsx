import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

import { Header, User, Home, Editor, Play } from './components'

function App() {
  const [message, setMessage] = useState('')
  useEffect(() => {
    fetch('/api')
      .then(res => res.json())
      .then(data => setMessage(data.message))
  }, [])

  return (
    <BrowserRouter>
      <div>
        <Header />
        <main style={{ padding: '1rem' }}>
          <p>{message}</p>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/editor" element={<Editor />} />
            <Route path="/play" element={<Play />} />
            <Route path="/user" element={<User />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
