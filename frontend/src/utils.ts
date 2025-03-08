// Constants
export const GAME_VERSION = 1;

const origin = () => {
  console.log(window.location.origin);
  return window.location.origin.split(":").slice(0, 2).join(":");
};

export const env = () => {
  const _origin = origin();
  console.log(_origin);
  if (
    _origin.includes("localhost") ||
    _origin.includes("12") ||
    _origin.includes("192")
  ) {
    return "DEV";
  }
  return "PROD";
};

export const backendUrl = () => `${origin()}${env() === "DEV" ? ":8001" : ""}`;
