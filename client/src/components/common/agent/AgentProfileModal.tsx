import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar } from '@/components/common/Avatar';
import { Loader2, Trophy, TrendingUp, TrendingDown, Minus, Target, Award, Calendar, History } from 'lucide-react';
import { agentsService } from '@/services/agentsService';
import { type AgentId } from '@/types/ids';
import { getEnvironmentTheme } from '@/lib/environmentThemes';
import { EnvironmentBackground } from '@/components/art/EnvironmentBackground';
import { useNavigate } from 'react-router-dom';

interface AgentGameRating {
  rating: number;
  gamesPlayed: number;
  gamesWon: number;
  gamesLost: number;
  gamesDrawn: number;
  highestRating: number;
  lowestRating: number;
}

interface RecentGameEntry {
  gameType: string;
  result: 'win' | 'loss' | 'draw';
  ratingChange: number;
  timestamp: string;
}

interface AgentProfileStats {
  gamesPlayed: number;
  gamesWon: number;
  gamesLost: number;
  gamesDrawn: number;
  winRate: number;
  recentForm: RecentGameEntry[];
}

interface AgentProfileData {
  agentId: string;
  name: string;
  description: string;
  gameEnvironment: string;
  avatarUrl: string | null;
  avatarType: string;
  isSystem: boolean;
  createdAt: string;
  overallStats: AgentProfileStats;
  gameRatings: Record<string, AgentGameRating>;
}

interface AgentProfileModalProps {
  agentId: AgentId | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const AgentProfileModal: React.FC<AgentProfileModalProps> = ({
  agentId,
  open,
  onOpenChange,
}) => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<AgentProfileData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gameHistory, setGameHistory] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    if (open && agentId) {
      loadProfile();
      loadGameHistory();
    }
  }, [open, agentId]);

  const loadProfile = async () => {
    if (!agentId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await agentsService.getAgentProfile(agentId);
      setProfile(data);
    } catch (err) {
      console.error('Failed to load agent profile:', err);
      setError('Failed to load agent profile');
    } finally {
      setLoading(false);
    }
  };

  const loadGameHistory = async () => {
    if (!agentId) return;

    setHistoryLoading(true);
    try {
      const games = await agentsService.getAgentGames(agentId, 10, 0);
      setGameHistory(games);
    } catch (err) {
      console.error('Failed to load game history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const getResultIcon = (result: string) => {
    switch (result) {
      case 'win':
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'loss':
        return <TrendingDown className="h-4 w-4 text-red-500" />;
      case 'draw':
        return <Minus className="h-4 w-4 text-yellow-500" />;
      default:
        return null;
    }
  };

  const getResultBadgeVariant = (result: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (result) {
      case 'win':
        return 'default';
      case 'loss':
        return 'destructive';
      case 'draw':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  const formatGameType = (gameType: string | undefined | null) => {
    if (!gameType) return 'Unknown';
    return gameType.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  if (!profile && !loading) {
    return null;
  }

  const theme = profile ? getEnvironmentTheme(profile.gameEnvironment as any) : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Agent Profile</DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-brand-teal" />
          </div>
        ) : error ? (
          <div className="text-center py-12 text-destructive">{error}</div>
        ) : profile ? (
          <div className="space-y-6">
            {/* Agent Header */}
            <Card className="relative overflow-hidden">
              {theme && <EnvironmentBackground environment={profile.gameEnvironment as any} opacity={0.08} className="absolute inset-0 pointer-events-none" />}
              <CardContent className="pt-6 relative z-10">
                <div className="flex flex-col md:flex-row gap-6 items-start">
                  <Avatar
                    src={profile.avatarUrl}
                    fallback={profile.name}
                    size="4xl"
                    type={profile.avatarType as any}
                    showBorder={true}
                  />
                  <div className="flex-1 space-y-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h2 className="text-2xl font-bold">{profile.name}</h2>
                        {profile.isSystem && (
                          <Badge variant="secondary">System</Badge>
                        )}
                      </div>
                      <p className="text-muted-foreground">{profile.description || 'No description provided'}</p>
                    </div>
                    <div className="flex flex-wrap gap-4 text-sm">
                      <div className="flex items-center gap-2">
                        <Target className="h-4 w-4 text-muted-foreground" />
                        <span className="text-muted-foreground">Environment:</span>
                        <span className="font-medium">{formatGameType(profile.gameEnvironment)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        <span className="text-muted-foreground">Created:</span>
                        <span className="font-medium">
                          {new Date(profile.createdAt).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Overall Statistics */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Trophy className="h-5 w-5 text-brand-teal" />
                  Overall Statistics
                </CardTitle>
              </CardHeader>
              <CardContent>
                                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-brand-teal">{profile.overallStats?.gamesPlayed ?? 0}</div>
                    <div className="text-sm text-muted-foreground">Games Played</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-500">{profile.overallStats?.gamesWon ?? 0}</div>
                    <div className="text-sm text-muted-foreground">Wins</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-500">{profile.overallStats?.gamesLost ?? 0}</div>
                    <div className="text-sm text-muted-foreground">Losses</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-yellow-500">{profile.overallStats?.gamesDrawn ?? 0}</div>
                    <div className="text-sm text-muted-foreground">Draws</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-brand-orange">{(profile.overallStats?.winRate ?? 0).toFixed(1)}%</div>
                    <div className="text-sm text-muted-foreground">Win Rate</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Game-Specific Ratings */}
            {profile.gameRatings && Object.keys(profile.gameRatings).length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Award className="h-5 w-5 text-brand-orange" />
                    Game Ratings
                  </CardTitle>
                  <CardDescription>Performance ratings for each game type</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Object.entries(profile.gameRatings).map(([gameType, rating]) => (
                      <div key={gameType} className="border rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-semibold">{formatGameType(gameType)}</h4>
                          <div className="text-2xl font-bold text-brand-teal">{Math.round(rating.rating)}</div>
                        </div>
                        <div className="grid grid-cols-3 md:grid-cols-6 gap-3 text-sm">
                          <div>
                            <div className="text-muted-foreground">Games</div>
                            <div className="font-medium">{rating.gamesPlayed}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Won</div>
                            <div className="font-medium text-green-500">{rating.gamesWon}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Lost</div>
                            <div className="font-medium text-red-500">{rating.gamesLost}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Drawn</div>
                            <div className="font-medium text-yellow-500">{rating.gamesDrawn}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Peak</div>
                            <div className="font-medium text-brand-orange">{Math.round(rating.highestRating)}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Lowest</div>
                            <div className="font-medium">{Math.round(rating.lowestRating)}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Recent Form */}
            {profile.overallStats.recentForm && profile.overallStats.recentForm.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Recent Form</CardTitle>
                  <CardDescription>Last {profile.overallStats.recentForm.length} games</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {profile.overallStats.recentForm.map((game, index) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center gap-3">
                          {getResultIcon(game.result)}
                          <div>
                            <div className="font-medium">{formatGameType(game.gameType)}</div>
                            <div className="text-sm text-muted-foreground">
                              {new Date(game.timestamp).toLocaleDateString()}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge variant={getResultBadgeVariant(game.result)}>
                            {game.result.toUpperCase()}
                          </Badge>
                          <div className={`text-sm font-medium ${game.ratingChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {game.ratingChange >= 0 ? '+' : ''}{Math.round(game.ratingChange)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Game History */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <History className="h-5 w-5 text-brand-teal" />
                  Game History
                </CardTitle>
                <CardDescription>Recent games played by this agent</CardDescription>
              </CardHeader>
              <CardContent>
                {historyLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : gameHistory.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No games played yet
                  </div>
                ) : (
                  <div className="space-y-2">
                    {gameHistory.map((game) => (
                      <div
                        key={game.id}
                        onClick={() => {
                          onOpenChange(false);
                          navigate(`/games/${game.gameType.toLowerCase()}/${game.id}`);
                        }}
                        className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                      >
                        <div className="flex-1">
                          <div className="font-medium">{formatGameType(game.gameType)}</div>
                          <div className="text-sm text-muted-foreground">
                            {game.finishedAt ? new Date(game.finishedAt).toLocaleDateString() : 'In Progress'}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {game.winnerId && (
                            <Badge variant={game.winnersIds?.includes(profile.agentId) ? 'default' : 'secondary'}>
                              {game.winnersIds?.includes(profile.agentId) ? 'Won' : 'Lost'}
                            </Badge>
                          )}
                          {game.drawReason && (
                            <Badge variant="outline">Draw</Badge>
                          )}
                          {!game.winnerId && !game.drawReason && game.matchmakingStatus === 'in_progress' && (
                            <Badge variant="outline">In Progress</Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
};

