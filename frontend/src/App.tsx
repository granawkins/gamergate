import { BrowserRouter, Routes, Route } from "react-router-dom";

import { Header, User, Home, Editor, Play } from "./components";
import { AuthProvider } from "./auth/AuthProvider";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div
          style={{
            height: "100vh",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <Header />
          <main
            style={{
              flex: 1,
              overflow: "auto",
            }}
          >
            <Routes>
              <Route
                path="/"
                element={
                  <div style={{ padding: "1rem" }}>
                    <Home />
                  </div>
                }
              />
              <Route
                path="/editor"
                element={
                  <div style={{ padding: "1rem" }}>
                    <Editor />
                  </div>
                }
              />
              <Route path="/play" element={<Play />} />
              <Route path="/play/:gameName" element={<Play />} />
              <Route
                path="/user"
                element={
                  <div style={{ padding: "1rem" }}>
                    <User />
                  </div>
                }
              />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
