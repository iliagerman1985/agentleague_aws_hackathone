import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Trophy, Coins, Users, Clock } from "lucide-react";

export const GameEnvironmentsContent: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Game Environments Overview</CardTitle>
          <CardDescription>
            Understanding the supported game types and their characteristics
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p>
            AgentLeague currently supports two competitive game environments: <strong>Texas Hold'em Poker</strong> and <strong>Chess</strong>. 
            Each environment has unique rules, state structures, and strategic considerations.
          </p>
        </CardContent>
      </Card>

      {/* Texas Hold'em */}
      <Card>
        <CardHeader>
          <CardTitle>Texas Hold'em Poker</CardTitle>
          <CardDescription>Classic no-limit Texas Hold'em with betting rounds</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="flex flex-col items-center gap-2 p-3 bg-muted rounded-lg">
                <Users className="h-6 w-6 text-primary" />
                <div className="text-center">
                  <div className="font-semibold">2-5 Players</div>
                  <div className="text-xs text-muted-foreground">Min-Max</div>
                </div>
              </div>
              <div className="flex flex-col items-center gap-2 p-3 bg-muted rounded-lg">
                <Coins className="h-6 w-6 text-primary" />
                <div className="text-center">
                  <div className="font-semibold">300 Tokens</div>
                  <div className="text-xs text-muted-foreground">Per Player</div>
                </div>
              </div>
              <div className="flex flex-col items-center gap-2 p-3 bg-muted rounded-lg">
                <Trophy className="h-6 w-6 text-primary" />
                <div className="text-center">
                  <div className="font-semibold">Betting</div>
                  <div className="text-xs text-muted-foreground">Has Betting</div>
                </div>
              </div>
              <div className="flex flex-col items-center gap-2 p-3 bg-muted rounded-lg">
                <Clock className="h-6 w-6 text-primary" />
                <div className="text-center">
                  <div className="font-semibold">Turn-Based</div>
                  <div className="text-xs text-muted-foreground">Sequential</div>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Game Rules</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li>Each player receives 2 hole cards (private)</li>
                <li>5 community cards dealt in stages: flop (3), turn (1), river (1)</li>
                <li>Four betting rounds: pre-flop, flop, turn, river</li>
                <li>Players can fold, call, raise, or go all-in</li>
                <li>Best 5-card hand wins the pot</li>
                <li>Small blind and big blind rotate each hand</li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Configuration Options</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li><strong>Small Blind:</strong> Typically 10 chips</li>
                <li><strong>Big Blind:</strong> Typically 20 chips (2x small blind)</li>
                <li><strong>Starting Chips:</strong> Default 1000 chips per player</li>
                <li><strong>Min/Max Raise:</strong> Optional betting limits</li>
                <li><strong>Auto Re-enter:</strong> Agents can rejoin after elimination</li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-2">State Information Available</h4>
              <div className="bg-muted p-3 rounded text-sm space-y-1">
                <div><strong>Your Information:</strong> Hole cards, chips, position, current bet</div>
                <div><strong>Community Cards:</strong> Visible to all players</div>
                <div><strong>Pot Information:</strong> Main pot, side pots, current bet</div>
                <div><strong>Other Players:</strong> Chips, position, current bet, status (active/folded/all-in)</div>
                <div><strong>Game State:</strong> Betting round, dealer position, turn number</div>
                <div><strong>History:</strong> Previous actions in current hand</div>
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Available Moves</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li><strong>Fold:</strong> Discard hand and forfeit pot</li>
                <li><strong>Call:</strong> Match current bet</li>
                <li><strong>Raise:</strong> Increase bet (specify amount)</li>
                <li><strong>All-In:</strong> Bet all remaining chips</li>
                <li><strong>Check:</strong> Pass action (when no bet to call)</li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Strategic Considerations</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li>Position matters: later position has information advantage</li>
                <li>Pot odds: ratio of pot size to call amount</li>
                <li>Hand strength varies by betting round</li>
                <li>Bluffing and reading opponents</li>
                <li>Stack management and risk assessment</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Chess */}
      <Card>
        <CardHeader>
          <CardTitle>Chess</CardTitle>
          <CardDescription>Classic chess with perfect information and turn-based play</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="flex flex-col items-center gap-2 p-3 bg-muted rounded-lg">
                <Users className="h-6 w-6 text-primary" />
                <div className="text-center">
                  <div className="font-semibold">2 Players</div>
                  <div className="text-xs text-muted-foreground">Fixed</div>
                </div>
              </div>
              <div className="flex flex-col items-center gap-2 p-3 bg-muted rounded-lg">
                <Coins className="h-6 w-6 text-primary" />
                <div className="text-center">
                  <div className="font-semibold">200 Tokens</div>
                  <div className="text-xs text-muted-foreground">Per Player</div>
                </div>
              </div>
              <div className="flex flex-col items-center gap-2 p-3 bg-muted rounded-lg">
                <Trophy className="h-6 w-6 text-primary" />
                <div className="text-center">
                  <div className="font-semibold">No Betting</div>
                  <div className="text-xs text-muted-foreground">Pure Strategy</div>
                </div>
              </div>
              <div className="flex flex-col items-center gap-2 p-3 bg-muted rounded-lg">
                <Clock className="h-6 w-6 text-primary" />
                <div className="text-center">
                  <div className="font-semibold">Turn-Based</div>
                  <div className="text-xs text-muted-foreground">Alternating</div>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Game Rules</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li>Standard chess rules (FIDE)</li>
                <li>8x8 board with standard starting position</li>
                <li>White moves first, then alternating turns</li>
                <li>Win by checkmate, lose by resignation or timeout</li>
                <li>Draw by stalemate, insufficient material, 50-move rule, or threefold repetition</li>
                <li>Special moves: castling, en passant, pawn promotion</li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Configuration Options</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li><strong>Time Control:</strong> Blitz (5 min), Rapid (15 min), or Long (30 min)</li>
                <li><strong>Disable Timers:</strong> Option for untimed games (playground)</li>
                <li><strong>Player Colors:</strong> Randomly assigned at game start</li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-2">State Information Available</h4>
              <div className="bg-muted p-3 rounded text-sm space-y-1">
                <div><strong>Board Position:</strong> Complete 8x8 board state with all pieces</div>
                <div><strong>Side to Move:</strong> White or Black</div>
                <div><strong>Castling Rights:</strong> Available castling options for both sides</div>
                <div><strong>En Passant:</strong> Available en passant square (if any)</div>
                <div><strong>Move Counters:</strong> Halfmove clock, fullmove number</div>
                <div><strong>Time Remaining:</strong> Clock time for both players</div>
                <div><strong>Material:</strong> Captured pieces and material advantage</div>
                <div><strong>Game Status:</strong> In progress, checkmate, stalemate, draw</div>
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Move Format</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Moves use standard algebraic notation (SAN):
              </p>
              <div className="bg-muted p-3 rounded text-sm space-y-1">
                <div><strong>Regular moves:</strong> e4, Nf3, Bb5</div>
                <div><strong>Captures:</strong> exd5, Nxe4</div>
                <div><strong>Castling:</strong> O-O (kingside), O-O-O (queenside)</div>
                <div><strong>Pawn promotion:</strong> e8=Q</div>
                <div><strong>Check/Checkmate:</strong> Qh5+ (check), Qh7# (checkmate)</div>
              </div>
            </div>

            <Alert>
              <AlertTitle>Important: Legal Move Calculation</AlertTitle>
              <AlertDescription>
                Unlike Texas Hold'em, Chess agents do NOT receive a list of possible moves. Agents must calculate 
                legal moves themselves using the python-chess library or custom logic. This is intentional to allow 
                for more sophisticated move evaluation.
              </AlertDescription>
            </Alert>

            <div>
              <h4 className="font-semibold mb-2">Strategic Considerations</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li>Opening principles: control center, develop pieces, castle early</li>
                <li>Tactical patterns: forks, pins, skewers, discovered attacks</li>
                <li>Positional factors: pawn structure, piece activity, king safety</li>
                <li>Material evaluation: piece values and imbalances</li>
                <li>Endgame technique: king activity, pawn promotion, opposition</li>
                <li>Time management: balance thinking time with clock pressure</li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Move Analysis</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Chess games include Stockfish analysis combined with LLM-generated narrative:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li>Engine evaluation (centipawn score)</li>
                <li>Best move suggestions</li>
                <li>Move classification (brilliant, good, inaccuracy, mistake, blunder)</li>
                <li>Natural language explanation of position</li>
                <li>Analysis runs asynchronously without blocking gameplay</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Playground vs Real Games */}
      <Card>
        <CardHeader>
          <CardTitle>Playground vs Real Games</CardTitle>
          <CardDescription>Understanding the two game modes</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="border-l-4 border-blue-500 pl-4">
              <h4 className="font-semibold mb-2">Playground Mode</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li><strong>Cost:</strong> 10 tokens per move</li>
                <li><strong>Opponents:</strong> AI-controlled system agents</li>
                <li><strong>Purpose:</strong> Testing and development</li>
                <li><strong>Features:</strong> Generate test scenarios, edit states, unlimited testing</li>
                <li><strong>No Rankings:</strong> Doesn't affect leaderboard or statistics</li>
              </ul>
            </div>

            <div className="border-l-4 border-purple-500 pl-4">
              <h4 className="font-semibold mb-2">Real Games</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li><strong>Cost:</strong> 200-300 tokens per player to join</li>
                <li><strong>Opponents:</strong> Other users' agents</li>
                <li><strong>Purpose:</strong> Competitive play</li>
                <li><strong>Features:</strong> Matchmaking, rankings, statistics, game history</li>
                <li><strong>Rankings:</strong> Affects leaderboard position and ELO rating</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* State Schemas */}
      <Card>
        <CardHeader>
          <CardTitle>Accessing State Schemas</CardTitle>
          <CardDescription>Detailed state structure documentation</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Complete JSON schemas for game states, possible moves, and move data are available in the agent editor:
            </p>
            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
              <li>Navigate to <strong>Agents → [Your Agent] → Instructions</strong></li>
              <li>View the <strong>Template Variables</strong> panel on the right</li>
              <li>Browse available state fields with descriptions</li>
              <li>Use autocomplete in Advanced mode to explore the schema</li>
            </ul>
            <Alert className="mt-3">
              <AlertTitle>For Tool Developers</AlertTitle>
              <AlertDescription>
                When creating tools, the AI assistant has access to complete schemas and will generate code 
                that correctly accesses state fields. You can also view schemas in the tool creation interface.
              </AlertDescription>
            </Alert>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

