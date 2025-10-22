import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, ChevronDown } from 'lucide-react';
import { agentsService, type AgentResponse, GameEnvironment } from '@/services/agentsService';

interface PlaygroundConfigProps {
  onCreatePlayground: (config: {
    agentId: string;
    smallBlind: number;
    bigBlind: number;
    startingChips: number;
    numPlayers: number;
  }) => void;
  isCreating?: boolean;
}

export const PlaygroundConfig: React.FC<PlaygroundConfigProps> = ({
  onCreatePlayground,
  isCreating = false,
}) => {
  const [agents, setAgents] = useState<AgentResponse[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [selectedAgentName, setSelectedAgentName] = useState<string>('Select an agent');
  const [smallBlind, setSmallBlind] = useState(10);
  const [bigBlind, setBigBlind] = useState(20);
  const [startingChips, setStartingChips] = useState(1000);
  const [numPlayers, setNumPlayers] = useState(4);
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadAgents = async () => {
      try {
        setIsLoadingAgents(true);
        setError(null);
        const response = await agentsService.list(GameEnvironment.TEXAS_HOLDEM);
        setAgents(response);
        
        // Pre-select the first agent if available
        if (response.length > 0) {
          setSelectedAgentId(response[0].id);
          setSelectedAgentName(response[0].name);
        }
      } catch (err) {
        console.error('Failed to load agents:', err);
        setError('Failed to load agents. Please try again.');
      } finally {
        setIsLoadingAgents(false);
      }
    };

    loadAgents();
  }, []);

  const handleCreatePlayground = async () => {
    if (!selectedAgentId) {
      setError('Please select an agent');
      return;
    }

    try {
      // Get the active version ID for the selected agent
      const activeVersion = await agentsService.getActiveVersion(selectedAgentId as any);
      if (!activeVersion) {
        setError('No active version found for the selected agent');
        return;
      }

      onCreatePlayground({
        agentId: activeVersion.id, // Use the active version ID instead of agent ID
        smallBlind,
        bigBlind,
        startingChips,
        numPlayers,
      });
    } catch (err) {
      console.error('Failed to get active version:', err);
      setError('Failed to get agent version. Please try again.');
    }
  };

  const isFormValid = selectedAgentId && smallBlind > 0 && bigBlind > smallBlind && startingChips > 0 && numPlayers >= 2 && numPlayers <= 5;

  if (isLoadingAgents) {
    return (
      <Card className="w-full max-w-md mx-auto rounded-lg">
        <CardContent className="flex items-center justify-center p-8">
          <Loader2 className="h-6 w-6 animate-spin mr-2" />
          <span>Loading agents...</span>
        </CardContent>
      </Card>
    );
  }

  if (error && agents.length === 0) {
    return (
      <Card className="w-full max-w-md mx-auto rounded-lg">
        <CardContent className="p-6">
          <div className="text-center text-red-600">
            <p className="mb-4">{error}</p>
            <Button 
              onClick={() => window.location.reload()} 
              variant="outline"
              className="rounded-lg"
            >
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (agents.length === 0) {
    return (
      <Card className="w-full max-w-md mx-auto rounded-lg">
        <CardContent className="p-6">
          <div className="text-center text-gray-600">
            <p className="mb-4">No agents available for Texas Hold'em.</p>
            <p className="text-sm">Create an agent first to play playground games.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md mx-auto rounded-lg">
      <CardHeader>
        <CardTitle>Create Playground Game</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg">
            {error}
          </div>
        )}
        
        <div className="space-y-2">
          <Label htmlFor="agent-select">Agent</Label>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                id="agent-select"
                variant="outline"
                className="w-full justify-between rounded-lg"
              >
                {selectedAgentName}
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-full">
              {agents.map((agent) => (
                <DropdownMenuItem
                  key={agent.id}
                  onClick={() => {
                    setSelectedAgentId(agent.id);
                    setSelectedAgentName(agent.name);
                  }}
                >
                  {agent.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="small-blind">Small Blind</Label>
            <Input
              id="small-blind"
              type="number"
              min="1"
              value={smallBlind}
              onChange={(e) => setSmallBlind(Number(e.target.value))}
              className="rounded-lg"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="big-blind">Big Blind</Label>
            <Input
              id="big-blind"
              type="number"
              min="2"
              value={bigBlind}
              onChange={(e) => setBigBlind(Number(e.target.value))}
              className="rounded-lg"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="starting-chips">Starting Chips</Label>
          <Input
            id="starting-chips"
            type="number"
            min="100"
            step="100"
            value={startingChips}
            onChange={(e) => setStartingChips(Number(e.target.value))}
            className="rounded-lg"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="num-players">Number of Players</Label>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                id="num-players"
                variant="outline"
                className="w-full justify-between rounded-lg"
              >
                {numPlayers} players
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-full">
              {[2, 3, 4, 5].map((num) => (
                <DropdownMenuItem
                  key={num}
                  onClick={() => setNumPlayers(num)}
                >
                  {num} players
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <Button
          onClick={handleCreatePlayground}
          disabled={!isFormValid || isCreating}
          className="w-full rounded-lg"
        >
          {isCreating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Creating...
            </>
          ) : (
            'Create Playground'
          )}
        </Button>
      </CardContent>
    </Card>
  );
};