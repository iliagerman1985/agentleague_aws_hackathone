import React from "react";
import { ChessGame } from "./ChessGame";

const ChessRealGameView: React.FC = () => {
  // Standalone real-game view uses default layout (not embedded)
  return <ChessGame />;
};

export default ChessRealGameView;

