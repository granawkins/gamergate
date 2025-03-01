import { useParams, Navigate } from "react-router-dom";
import { GameFrame } from "./GameFrame";

export const Play = () => {
  const { gameName } = useParams();

  // Redirect to home if no gameName is provided
  if (!gameName) {
    return <Navigate to="/" replace />;
  }

  return <GameFrame gameName={gameName} title={gameName} />;
};
