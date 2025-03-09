import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";

import {
  Admin,
  Header,
  User,
  Home,
  Editor,
  Play,
  StripeCheckout,
  StripeReturn,
} from "./components";
import { AuthProvider } from "./auth/AuthProvider";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div
          className="app-container"
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
              <Route path="/" element={<Home />} />
              <Route path="/editor" element={<Editor />} />
              <Route path="/editor/:gameName" element={<Editor />} />
              <Route path="/play/:gameName" element={<Play />} />
              <Route path="/user" element={<User />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/checkout" element={<StripeCheckout />} />
              <Route path="/return" element={<StripeReturn />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
