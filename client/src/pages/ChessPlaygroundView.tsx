import React from "react";
import ChessPlaygroundPanel from "./ChessPlaygroundPanel";

interface Props {
  initialGameId: string;
  onGameEnded?: () => void;
  onReset?: () => void;
}

const ChessPlaygroundView: React.FC<Props> = ({ initialGameId, onGameEnded, onReset }) => {
  return (
    <ChessPlaygroundPanel initialGameId={initialGameId} onGameEnded={onGameEnded} onReset={onReset} />
  );
};

export default ChessPlaygroundView;

