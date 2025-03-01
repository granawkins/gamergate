import { Game } from "../types";

interface GameInfoTabProps {
  gameInfo: Game | null;
  isLoading: boolean;
}

export const GameInfoTab = ({ gameInfo, isLoading }: GameInfoTabProps) => {
  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "1rem",
      }}
    >
      {isLoading ? (
        <div
          style={{
            textAlign: "center",
            color: "#888",
            marginTop: "2rem",
          }}
        >
          Loading game information...
        </div>
      ) : gameInfo ? (
        <div>
          <h2>Game Information</h2>
          <div style={{ marginTop: "1rem" }}>
            {Object.entries(gameInfo).map(([key, value]) => (
              <div
                key={key}
                style={{
                  display: "flex",
                  padding: "0.5rem 0",
                  borderBottom: "1px solid #eee",
                }}
              >
                <div
                  style={{
                    fontWeight: "bold",
                    width: "120px",
                    flexShrink: 0,
                  }}
                >
                  {key}:
                </div>
                <div>{String(value)}</div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div
          style={{
            textAlign: "center",
            color: "#888",
            marginTop: "2rem",
          }}
        >
          Failed to load game information
        </div>
      )}
    </div>
  );
};
