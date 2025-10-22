import React, { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { ChevronDown, Plus, Users, Gamepad2 } from 'lucide-react';
import { agentsService, GameEnvironment, AgentResponse } from '@/services/agentsService';
import { toast } from 'sonner';

interface Player {
  id: string;
  name: string;
  chipCount: number;
  isActive?: boolean;
  isFolded?: boolean;
  isAllIn?: boolean;
  currentBet?: number;
}

interface GameControlsProps {
  gameId?: string;
  gameStatus?: 'waiting' | 'active' | 'finished';
  playerCount?: number;
  maxPlayers?: number;
  isHost?: boolean;
  isInGame?: boolean;
  onCreateGame?: (config: GameConfig) => void;
  onCreatePlayground?: (config: PlaygroundConfig) => void;
  onJoinGame?: () => void;
  onStartGame?: () => void;
  onLeaveGame?: () => void;
  className?: string;
  // Enhanced props for in-game information
  pot?: number;
  bettingRound?: string;
  smallBlind?: number;
  bigBlind?: number;
  players?: Player[];
  currentPlayerId?: string;
}

interface PlaygroundConfig {
  smallBlind: number;
  bigBlind: number;
  startingChips: number;
  numPlayers: number;
  selectedAgentId: string;
}

interface GameConfig {
  buyIn: number;
  smallBlind: number;
  bigBlind: number;
  maxPlayers: number;
  selectedAgentId: string | null;
}

export const GameControls: React.FC<GameControlsProps> = ({
  gameId,
  gameStatus = 'waiting',
  playerCount = 0,
  maxPlayers = 5,
  isHost = false,
  isInGame = false,
  onCreateGame,
  onCreatePlayground,
  onJoinGame,
  onStartGame,
  onLeaveGame,
  className,
  pot = 0,
  bettingRound = 'Pre-flop',
  smallBlind = 0,
  bigBlind = 0,
  players = [],
  currentPlayerId
}) => {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showPlaygroundForm, setShowPlaygroundForm] = useState(false);
  const [gameConfig, setGameConfig] = useState<GameConfig>({
    buyIn: 1000,
    smallBlind: 10,
    bigBlind: 20,
    maxPlayers: 5,
    selectedAgentId: null
  });
  const [playgroundConfig, setPlaygroundConfig] = useState<PlaygroundConfig>({
    smallBlind: 10,
    bigBlind: 20,
    startingChips: 1000,
    numPlayers: 4,
    selectedAgentId: ''
  });
  const [availableAgents, setAvailableAgents] = useState<AgentResponse[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);

  // Fetch available Texas Hold'em agents
  useEffect(() => {
    const fetchAgents = async () => {
      setLoadingAgents(true);
      try {
        const agents = await agentsService.list(GameEnvironment.TEXAS_HOLDEM);
        const activeAgents = agents.filter(agent => agent.isActive);
        setAvailableAgents(activeAgents);
        
        // Auto-select the first available agent for both configs
        if (activeAgents.length > 0) {
          const firstAgentId = activeAgents[0].id.toString();
          setGameConfig(prev => ({ ...prev, selectedAgentId: firstAgentId }));
          setPlaygroundConfig(prev => ({ ...prev, selectedAgentId: firstAgentId }));
        }
      } catch (error) {
        console.error('Failed to fetch agents:', error);
        toast.error('Failed to load available agents');
      } finally {
        setLoadingAgents(false);
      }
    };

    fetchAgents();
  }, []);

  const handleCreateGame = () => {
    if (!gameConfig.selectedAgentId) {
      toast.error('Please select an agent to play with');
      return;
    }
    onCreateGame?.(gameConfig);
    setShowCreateForm(false);
  };

  const handleCreatePlayground = () => {
    if (!playgroundConfig.selectedAgentId) {
      toast.error('Please select an agent for the playground');
      return;
    }
    onCreatePlayground?.(playgroundConfig);
    setShowPlaygroundForm(false);
  };

  const handleJoinGame = () => {
    onJoinGame?.();
  };

  const getStatusVariant = () => {
    switch (gameStatus) {
      case 'waiting': return 'secondary';
      case 'active': return 'default';
      case 'finished': return 'outline';
      default: return 'outline';
    }
  };

  return (
    <div className={cn('w-full max-w-md space-y-6', className)}>
      {!isInGame ? (
        <>
          {/* Status Badge */}
          {gameId && (
            <div className="flex justify-center">
              <Badge variant={getStatusVariant()} className="text-sm px-3 py-1">
                {gameStatus.toUpperCase()}
              </Badge>
            </div>
          )}
          
          {/* Main Action Buttons */}
          <div className="grid grid-cols-1 gap-4">
            <Button
              onClick={() => {
                setShowCreateForm(!showCreateForm);
                setShowPlaygroundForm(false);
              }}
              variant={showCreateForm ? "secondary" : "default"}
              size="lg"
              className="h-14 text-base font-semibold shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-[1.02]"
            >
              <Plus className="w-5 h-5 mr-2" />
              {showCreateForm ? 'Cancel Creation' : 'Create New Game'}
            </Button>
            
            <Button
              onClick={() => {
                setShowPlaygroundForm(!showPlaygroundForm);
                setShowCreateForm(false);
              }}
              variant={showPlaygroundForm ? "secondary" : "outline"}
              size="lg"
              className="h-14 text-base font-semibold border-2 hover:border-primary/50 transition-all duration-200 hover:scale-[1.02]"
            >
              <Gamepad2 className="w-5 h-5 mr-2" />
              {showPlaygroundForm ? 'Cancel Playground' : 'Playground'}
            </Button>
            
            <Button
              onClick={handleJoinGame}
              variant="outline"
              size="lg"
              className="h-14 text-base font-semibold border-2 hover:border-primary/50 transition-all duration-200 hover:scale-[1.02]"
            >
              <Users className="w-5 h-5 mr-2" />
              Find Match
            </Button>
          </div>
              
          {showCreateForm && (
            <div className="space-y-4 p-4 border-2 rounded-xl bg-muted/30 backdrop-blur-sm shadow-lg">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label htmlFor="buyIn">Buy-in ($)</Label>
                      <Input
                        id="buyIn"
                        type="number"
                        value={gameConfig.buyIn}
                        onChange={(e) => setGameConfig(prev => ({ ...prev, buyIn: parseInt(e.target.value) || 0 }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="maxPlayers">Max Players</Label>
                      <Input
                        id="maxPlayers"
                        type="number"
                        min="2"
                        max="5"
                        value={gameConfig.maxPlayers}
                        onChange={(e) => setGameConfig(prev => ({ ...prev, maxPlayers: parseInt(e.target.value) || 2 }))}
                      />
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label htmlFor="smallBlind">Small Blind ($)</Label>
                      <Input
                        id="smallBlind"
                        type="number"
                        value={gameConfig.smallBlind}
                        onChange={(e) => setGameConfig(prev => ({ ...prev, smallBlind: parseInt(e.target.value) || 0 }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="bigBlind">Big Blind ($)</Label>
                      <Input
                        id="bigBlind"
                        type="number"
                        value={gameConfig.bigBlind}
                        onChange={(e) => setGameConfig(prev => ({ ...prev, bigBlind: parseInt(e.target.value) || 0 }))}
                      />
                    </div>
                  </div>

                  {/* Agent Selection */}
                  <div>
                    <Label htmlFor="agentSelect">Select Your Agent</Label>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="outline"
                          className="w-full justify-between"
                          disabled={loadingAgents}
                        >
                          {gameConfig.selectedAgentId ? (
                            (() => {
                              const selectedAgent = availableAgents.find(a => a.id.toString() === gameConfig.selectedAgentId);
                              return selectedAgent ? selectedAgent.name : 'Unknown Agent';
                            })()
                          ) : (
                            loadingAgents ? "Loading agents..." : "Choose an agent"
                          )}
                          <ChevronDown className="h-4 w-4 opacity-50" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent className="w-full">
                        {availableAgents.map((agent) => (
                          <DropdownMenuItem
                            key={agent.id}
                            onClick={() => setGameConfig(prev => ({ ...prev, selectedAgentId: agent.id.toString() }))}
                          >
                            <div className="flex flex-col">
                              <span className="font-medium">{agent.name}</span>
                              {agent.description && (
                                <span className="text-sm text-muted-foreground">{agent.description}</span>
                              )}
                            </div>
                          </DropdownMenuItem>
                        ))}
                        {availableAgents.length === 0 && !loadingAgents && (
                          <DropdownMenuItem disabled>
                            No Texas Hold'em agents available
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                    {availableAgents.length === 0 && !loadingAgents && (
                      <p className="text-sm text-muted-foreground mt-1">
                        You need to create a Texas Hold'em agent first.
                      </p>
                    )}
                  </div>
                  
                  <Button onClick={handleCreateGame} className="w-full">
                    Create Game
                  </Button>
                </div>
              )}
              
          {showPlaygroundForm && (
            <div className="space-y-4 p-4 border-2 rounded-xl bg-muted/30 backdrop-blur-sm shadow-lg">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label htmlFor="playgroundStartingChips">Starting Chips ($)</Label>
                      <Input
                        id="playgroundStartingChips"
                        type="number"
                        value={playgroundConfig.startingChips}
                        onChange={(e) => setPlaygroundConfig(prev => ({ ...prev, startingChips: parseInt(e.target.value) || 0 }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="playgroundNumPlayers">Players</Label>
                      <Input
                        id="playgroundNumPlayers"
                        type="number"
                        min="2"
                        max="6"
                        value={playgroundConfig.numPlayers}
                        onChange={(e) => setPlaygroundConfig(prev => ({ ...prev, numPlayers: parseInt(e.target.value) || 2 }))}
                      />
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label htmlFor="playgroundSmallBlind">Small Blind ($)</Label>
                      <Input
                        id="playgroundSmallBlind"
                        type="number"
                        value={playgroundConfig.smallBlind}
                        onChange={(e) => setPlaygroundConfig(prev => ({ ...prev, smallBlind: parseInt(e.target.value) || 0 }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="playgroundBigBlind">Big Blind ($)</Label>
                      <Input
                        id="playgroundBigBlind"
                        type="number"
                        value={playgroundConfig.bigBlind}
                        onChange={(e) => setPlaygroundConfig(prev => ({ ...prev, bigBlind: parseInt(e.target.value) || 0 }))}
                      />
                    </div>
                  </div>

                  {/* Agent Selection for Playground */}
                  <div>
                    <Label htmlFor="playgroundAgentSelect">Select Agent</Label>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="outline"
                          className="w-full justify-between"
                          disabled={loadingAgents}
                        >
                          {playgroundConfig.selectedAgentId ? (
                            (() => {
                              const selectedAgent = availableAgents.find(a => a.id.toString() === playgroundConfig.selectedAgentId);
                              return selectedAgent ? selectedAgent.name : 'Unknown Agent';
                            })()
                          ) : (
                            loadingAgents ? "Loading agents..." : "Choose an agent"
                          )}
                          <ChevronDown className="h-4 w-4 opacity-50" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent className="w-full">
                        {availableAgents.map((agent) => (
                          <DropdownMenuItem
                            key={agent.id}
                            onClick={() => setPlaygroundConfig(prev => ({ ...prev, selectedAgentId: agent.id.toString() }))}
                          >
                            <div className="flex flex-col">
                              <span className="font-medium">{agent.name}</span>
                              {agent.description && (
                                <span className="text-sm text-muted-foreground">{agent.description}</span>
                              )}
                            </div>
                          </DropdownMenuItem>
                        ))}
                        {availableAgents.length === 0 && !loadingAgents && (
                          <DropdownMenuItem disabled>
                            No Texas Hold'em agents available
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                    {availableAgents.length === 0 && !loadingAgents && (
                      <p className="text-sm text-muted-foreground mt-1">
                        You need to create a Texas Hold'em agent first.
                      </p>
                    )}
                  </div>
                  
                  <Button onClick={handleCreatePlayground} className="w-full">
                    Start Playground
                  </Button>
                </div>
              )}


        </>
      ) : (
          <>
            {/* In-Game Information */}
            <div className="space-y-4">
              {/* Game Status */}
              <div className="space-y-2">
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">Current Phase</div>
                  <div className="text-lg font-semibold">{bettingRound}</div>
                </div>
                
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div>
                    <div className="text-sm text-muted-foreground">Pot</div>
                    <div className="text-lg font-bold text-primary">${pot.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Players</div>
                    <div className="text-lg">{playerCount} / {maxPlayers}</div>
                  </div>
                </div>
              </div>

              {/* Game Settings */}
              <div className="border-t pt-3">
                <div className="text-sm font-medium mb-2">Game Settings</div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Small Blind:</span>
                    <span>${smallBlind}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Big Blind:</span>
                    <span>${bigBlind}</span>
                  </div>
                </div>
                <div className="flex justify-between text-sm mt-1">
                  <span className="text-muted-foreground">Game ID:</span>
                  <span className="font-mono text-xs">{gameId}</span>
                </div>
              </div>

              {/* Players List */}
              {players.length > 0 && (
                <div className="border-t pt-3">
                  <div className="text-sm font-medium mb-2">Players</div>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {players.map((player) => (
                      <div key={player.id} className={cn(
                        "flex items-center justify-between p-2 rounded text-sm",
                        player.id === currentPlayerId ? "bg-primary/10 border border-primary/20" : "bg-muted/50",
                        player.isFolded && "opacity-50"
                      )}>
                        <div className="flex items-center space-x-2">
                          <div className={cn(
                            "w-2 h-2 rounded-full",
                            player.isActive ? "bg-green-500" : player.isFolded ? "bg-red-500" : "bg-gray-400"
                          )} />
                          <span className={cn(
                            "font-medium",
                            player.id === currentPlayerId && "text-primary"
                          )}>
                            {player.name}
                            {player.id === currentPlayerId && " (You)"}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">${player.chipCount.toLocaleString()}</div>
                          {(player.currentBet || 0) > 0 && (
                            <div className="text-xs text-muted-foreground">Bet: ${player.currentBet || 0}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Game Actions */}
              <div className="border-t pt-3 space-y-2">
                {isHost && gameStatus === 'waiting' && (
                  <Button onClick={onStartGame} className="w-full" disabled={playerCount < 2}>
                    Start Game
                  </Button>
                )}
                
                <Button onClick={onLeaveGame} variant="destructive" className="w-full">
                  Leave Game
                </Button>
              </div>
            </div>
          </>
        )}
    </div>
  );
};

export default GameControls;
