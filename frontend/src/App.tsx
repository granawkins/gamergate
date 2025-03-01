import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";

import { Header, User, Home, Editor, Play } from "./components";
import { AuthProvider } from "./auth/AuthProvider";

// Wrapper component to conditionally apply padding
const MainContent = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  const isPlayRoute = location.pathname.startsWith('/play/');
  
  return (
    <main style={{ 
      padding: isPlayRoute ? 0 : "1rem",
      height: "calc(100vh - 60px)", // Assuming header is about 60px
      overflow: isPlayRoute ? 'hidden' : 'auto'
    }}>
      {children}
    </main>
  );
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
          <Header />
          <Routes>
            <Route path="/" element={<MainContent><Home /></MainContent>} />
            <Route path="/editor" element={<MainContent><Editor /></MainContent>} />
            <Route path="/play" element={<MainContent><Play /></MainContent>} />
            <Route path="/play/:gameName" element={<MainContent><Play /></MainContent>} />
            <Route path="/user" element={<MainContent><User /></MainContent>} />
          </Routes>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
