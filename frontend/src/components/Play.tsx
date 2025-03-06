import { useParams, Navigate } from "react-router-dom";
import { GameFrame } from "./GameFrame";
import { Header } from "./Header";

export const Play = () => {
  const { gameName } = useParams();

  // Redirect to home if no gameName is provided
  if (!gameName) {
    return <Navigate to="/" replace />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Header gameName={gameName} />
      <div style={{ flex: 1, position: "relative" }}>
        <GameFrame gameName={gameName} title={gameName} />
      </div>
    </div>
  );
};
