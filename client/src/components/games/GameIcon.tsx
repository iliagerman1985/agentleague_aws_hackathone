import React from "react";
import { GameEnvironment } from "@/services/agentsService";

interface GameIconProps {
  environment: GameEnvironment | string;
  size?: number; // px
  className?: string;
  alt?: string;
}

const environmentToIconSrc = (env: string): string => {
  switch (env) {
    case "texas_holdem":
      return "/icons/games/poker.svg";
    default:
      return "/icon.svg"; // fallback app icon
  }
};

export const GameIcon: React.FC<GameIconProps> = ({ environment, size = 16, className = "", alt }) => {
  const e = typeof environment === "string" ? environment : String(environment);
  const src = environmentToIconSrc(e);
  const computedAlt = alt ?? `${e} icon`;
  return (
    <img
      src={src}
      alt={computedAlt}
      width={size}
      height={size}
      className={className}
      style={{ width: `${size}px`, height: `${size}px` }}
    />
  );
};

export default GameIcon;

