import React from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { SharedModal } from "@/components/common/SharedModal";
import { Trophy, Play, Eye } from "lucide-react";
import Ballpit from "@/components/Ballpit";

interface GameVictoryModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isVictory: boolean;
  gameId: string;
  gameType: string;
  endReason?: string; // e.g., "checkmate", "resignation", "timeout", "stalemate"
}

export const GameVictoryModal: React.FC<GameVictoryModalProps> = ({
  open,
  onOpenChange,
  isVictory,
  gameId,
  gameType,
  endReason,
}) => {
  const navigate = useNavigate();

  // Format the end reason for display
  const formatEndReason = (reason?: string): string => {
    if (!reason) return "";

    // Handle specific reasons
    switch (reason.toLowerCase()) {
      case "checkmate":
        return "by checkmate";
      case "resignation":
        return "by resignation";
      case "timeout":
        return "by timeout";
      case "failed_to_move":
        return "opponent failed to move";
      case "stalemate":
        return "by stalemate";
      case "fifty_moves":
        return "by fifty-move rule";
      case "threefold_repetition":
        return "by threefold repetition";
      case "insufficient_material":
        return "by insufficient material";
      case "time":
        return "by timeout";
      case "timeout_insufficient_material":
        return "by timeout (insufficient material)";
      default:
        // Convert snake_case to readable format
        return reason.replace(/_/g, " ");
    }
  };

  const reasonText = formatEndReason(endReason);

  const handlePlayAgain = () => {
    onOpenChange(false);
    // Navigate to the game lobby/matchmaking
    navigate(`/games/${gameType}`);
  };

  const handleShowReplay = () => {
    onOpenChange(false);
    // Navigate to the replay page
    navigate(`/games/${gameType}/${gameId}/replay`);
  };

  return (
    <>
      {/* Ballpit background - only shown on victory */}
      {open && isVictory && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            zIndex: 9998,
            pointerEvents: "none",
          }}
          aria-hidden="true"
        >
          <Ballpit
            count={200}
            gravity={0.05}
            friction={0.99}
            wallBounce={0.95}
            followCursor={true}
            colors={[0x93c5fd, 0x0891b2, 0xea580c, 0xd1d5db, 0x6ee7b7]}
          />
        </div>
      )}

      {/* Modal */}
      <SharedModal
        open={open}
        onOpenChange={onOpenChange}
        title={isVictory ? "🎉 Congratulations!" : "Game Over"}
        description={
          isVictory
            ? `Your agent won the game${reasonText ? ` ${reasonText}` : ""}!`
            : `Your agent lost the game${reasonText ? ` ${reasonText}` : ""}.`
        }
        size="md"
        contentProps={{ style: { zIndex: 9999 } }}
        footer={
          <div className="flex flex-col sm:flex-row gap-2 w-full">
            <Button
              onClick={handlePlayAgain}
              variant="default"
              className="flex-1 flex items-center justify-center gap-2"
            >
              <Play className="h-4 w-4" />
              Play Again
            </Button>
            <Button
              onClick={handleShowReplay}
              variant="outline"
              className="flex-1 flex items-center justify-center gap-2"
            >
              <Eye className="h-4 w-4" />
              Show Replay
            </Button>
          </div>
        }
      >
        <div className="flex flex-col items-center justify-center py-6 space-y-4">
          {isVictory ? (
            <>
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-brand-teal to-brand-mint flex items-center justify-center animate-bounce">
                <Trophy className="w-12 h-12 text-white" />
              </div>
              <p className="text-lg font-semibold text-center">
                Victory is yours!
              </p>
              <p className="text-sm text-muted-foreground text-center max-w-sm">
                Your agent demonstrated superior strategy and skill. Ready for another challenge?
              </p>
            </>
          ) : (
            <>
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-gray-400 to-gray-600 flex items-center justify-center">
                <Trophy className="w-12 h-12 text-white opacity-50" />
              </div>
              <p className="text-lg font-semibold text-center">
                Not this time
              </p>
              <p className="text-sm text-muted-foreground text-center max-w-sm">
                Every game is a learning opportunity. Analyze the replay and come back stronger!
              </p>
            </>
          )}
        </div>
      </SharedModal>
    </>
  );
};

export default GameVictoryModal;

