import { BrowserRouter, Routes, Route } from "react-router-dom";

import { Header, User, Home, Editor, Play } from "./components";
import { AuthProvider } from "./auth/AuthProvider";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div>
          <Header />
          <main style={{ padding: "1rem" }}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/editor" element={<Editor />} />
              <Route path="/play" element={<Play />} />
              <Route path="/play/:gameName" element={<Play />} />
              <Route path="/user" element={<User />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
