import React, { useEffect, useState } from "react";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { ActionTable } from "@/components/common/tables/ActionTable";
import { Badge } from "@/components/ui/badge";
import { PageBackground } from "@/components/common/layout/PageBackground";
import { Trophy, Filter } from "lucide-react";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { leaderboardService, LeaderboardEntry } from "@/services/leaderboardService";
import { GameType } from "@/types/game";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Avatar } from "@/components/common/Avatar";
import { useAgentProfile } from "@/hooks/useAgentProfile";
import { AgentProfileModal } from "@/components/common/agent/AgentProfileModal";
import { AgentId } from "@/types/ids";
import { getAvailableGameEnvironments } from "@/services/agentsService";

export const Leaderboard: React.FC = () => {
	const [leaderboardData, setLeaderboardData] = useState<LeaderboardEntry[]>([]);
	const [loading, setLoading] = useState(true);
	const [gameTypeFilter, setGameTypeFilter] = useState<GameType | "all">("all");
	const { showAgentProfile, selectedAgentId, isProfileOpen, closeAgentProfile } = useAgentProfile();

	// Get available game environments for the filter dropdown
	const availableGameTypes = getAvailableGameEnvironments();

	// Show winnings only for Texas Hold'em (poker)
	const showWinnings = gameTypeFilter === "texas_holdem";

	const handleAgentClick = (agentId: string) => {
		console.log('[Leaderboard] Agent clicked:', agentId);
		showAgentProfile(agentId as AgentId);
		console.log('[Leaderboard] After showAgentProfile call');
	};

	useEffect(() => {
		const loadLeaderboard = async () => {
			setLoading(true);
			try {
				const filter = gameTypeFilter === "all" ? undefined : gameTypeFilter;
				const data = await leaderboardService.getLeaderboard(filter);
				console.log('[Leaderboard] Loaded data:', data);
				console.log('[Leaderboard] First entry:', data[0]);

				// Filter by available environments when showing "all"
				const filteredData = gameTypeFilter === "all"
					? data.filter(entry => {
						const availableEnvs = getAvailableGameEnvironments();
						return entry.gameRatings && Object.keys(entry.gameRatings).some(env =>
							availableEnvs.includes(env as any)
						);
					})
					: data;

				setLeaderboardData(filteredData);
			} catch (error) {
				console.error("Failed to load leaderboard:", error);
			} finally {
				setLoading(false);
			}
		};

		void loadLeaderboard();
	}, [gameTypeFilter]);

	const getRankIcon = (rank: number) => {
		if (rank === 1) return <Trophy className="w-5 h-5 text-yellow-500 dark:text-yellow-400" />;
		if (rank === 2) return <Trophy className="w-5 h-5 text-gray-500 dark:text-gray-400" />;
		if (rank === 3) return <Trophy className="w-5 h-5 text-amber-600 dark:text-amber-600" />;
		return <span className="font-semibold text-sm">{rank}</span>;
	};

	const getRankBadgeColor = (rank: number) => {
		if (rank === 1) return "bg-yellow-500/30 text-yellow-600 border-yellow-500/50 dark:bg-yellow-500/20 dark:text-yellow-400 dark:border-yellow-500/30";
		if (rank === 2) return "bg-gray-500/30 text-gray-600 border-gray-500/50 dark:bg-gray-500/20 dark:text-gray-400 dark:border-gray-500/30";
		if (rank === 3) return "bg-amber-500/30 text-amber-700 border-amber-500/50 dark:bg-amber-500/20 dark:text-amber-400 dark:border-amber-500/30";
		return "bg-muted text-muted-foreground";
	};

	// Transform data to include rank and calculate winnings
	const rankedData = leaderboardData.map((entry, index) => {
		const rating = gameTypeFilter !== "all" && entry.gameRatings?.[gameTypeFilter]
			? entry.gameRatings[gameTypeFilter].rating
			: entry.gameRatings
				? Object.values(entry.gameRatings).reduce((max, r) => Math.max(max, r.gamesPlayed > 0 ? r.rating : 0), 0)
				: 0;

		const winnings = leaderboardService.calculateWinnings(entry, gameTypeFilter !== "all" ? gameTypeFilter : undefined);

		// Format player display name: "username (agent name)" or just "agent name" for system agents
		const playerDisplay = entry.isSystem
			? entry.name
			: entry.username
				? `${entry.username} (${entry.name})`
				: entry.name;

		console.log('[Leaderboard] Processing entry:', {
			name: entry.name,
			agentId: entry.agentId,
			avatarUrl: entry.avatarUrl,
			avatarType: entry.avatarType
		});

		return {
			rank: index + 1,
			player: playerDisplay,
			agentId: entry.agentId,
			avatarUrl: entry.avatarUrl,
			avatarType: entry.avatarType,
			is_system: entry.isSystem,
			game: leaderboardService.getGameEnvironmentDisplay(entry.gameEnvironment),
			games: entry.overallStats?.gamesPlayed ?? 0,
			winrate: `${(entry.overallStats?.winRate ?? 0).toFixed(1)}%`,
			winnings,
			rating: Math.round(rating),
		};
	});

	return (
		<PageBackground variant="waves">
			<PageContainer className="flex flex-col">
				<div className="w-full max-w-[95rem] mx-auto space-y-8">
				<div className="relative mb-8 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6">
					<div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
						<EnvironmentBackground environment="leaderboard" opacity={0.20} />
					</div>
					<div className="relative z-10">
						<PageHeader title="Leaderboard" subtitle="Top performing agents and players" />
					</div>
				</div>

				{/* Filter Section */}
				<div className="flex items-center gap-3">
					<Filter className="h-5 w-5 text-muted-foreground" />
					<Select value={gameTypeFilter} onValueChange={(value) => setGameTypeFilter(value as GameType | "all")}>
						<SelectTrigger className="w-[200px]">
							<SelectValue placeholder="Filter by game" />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value="all">All Games</SelectItem>
							{availableGameTypes.map((gameType) => (
								<SelectItem key={gameType} value={gameType}>
									{leaderboardService.getGameEnvironmentDisplay(gameType)}
								</SelectItem>
							))}
						</SelectContent>
					</Select>
				</div>

				<div className="flex-1 flex flex-col min-h-0">
				{/* Mobile Card View */}
				<div className="block lg:hidden">
					<div className="space-y-3">
						{loading ? (
							<div className="text-center py-8 text-muted-foreground">Loading...</div>
						) : rankedData.length === 0 ? (
							<div className="text-center py-8 text-muted-foreground">No leaderboard data available.</div>
						) : (
							rankedData.map((player) => (
								<div key={player.agentId} className="bg-card border rounded-xl p-4 shadow-sm">
									<div className="flex items-center justify-between mb-3">
										<div className="flex items-center gap-3">
											<div className={`flex items-center justify-center w-8 h-8 rounded-full border ${getRankBadgeColor(player.rank)}`}>
												{getRankIcon(player.rank)}
											</div>
											<div 
												className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
												onClick={() => handleAgentClick(player.agentId)}
												role="button"
												tabIndex={0}
												onKeyDown={(e) => {
													if (e.key === 'Enter' || e.key === ' ') {
														e.preventDefault();
														handleAgentClick(player.agentId);
													}
												}}
											>
												<Avatar 
													src={player.avatarUrl}
													type={player.avatarType as any}
													fallback={player.player}
													className="w-8 h-8"
												/>
												<div className="flex flex-col">
													<span className="font-medium text-sm truncate">{player.player}</span>
													<div className="flex items-center gap-2">
														{gameTypeFilter === "all" && (
															<span className="text-xs text-muted-foreground">{player.game}</span>
														)}
														{player.is_system && (
															<Badge variant="secondary" className="text-xs w-fit">System</Badge>
														)}
													</div>
												</div>
											</div>
										</div>
										{showWinnings && (
											<Badge variant={player.winnings >= 0 ? "secondary" : "destructive"} className="text-xs">
												${player.winnings.toLocaleString()}
											</Badge>
										)}
									</div>
									<div className={`grid ${showWinnings ? 'grid-cols-3' : 'grid-cols-3'} gap-4 text-sm`}>
										<div className="text-center">
											<p className="text-muted-foreground text-xs mb-1">Games</p>
											<p className="font-medium">{player.games}</p>
										</div>
										<div className="text-center">
											<p className="text-muted-foreground text-xs mb-1">Win Rate</p>
											<p className="font-medium">{player.winrate}</p>
										</div>
										<div className="text-center">
											<p className="text-muted-foreground text-xs mb-1">Rating</p>
											<p className="font-semibold text-brand-teal">{player.rating}</p>
										</div>
									</div>
								</div>
							))
						)}
					</div>
				</div>

				{/* Desktop Table View */}
				<div className="hidden lg:block w-full flex-1">
					<div className="flex-1 overflow-y-auto pt-6">
						<ActionTable
							data={rankedData}
							actions={[]}
							className="bg-transparent"
							columns={[
								{
									key: 'rank',
									header: 'Rank',
									render: (item) => (
										<div className={`flex items-center justify-center w-8 h-8 rounded-full border ${getRankBadgeColor(item.rank)}`}>
											{getRankIcon(item.rank)}
										</div>
									)
								},
								{
									key: 'player',
									header: 'Player',
									render: (item) => (
										<div 
											className="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity"
											onClick={() => handleAgentClick(item.agentId)}
											role="button"
											tabIndex={0}
											onKeyDown={(e) => {
												if (e.key === 'Enter' || e.key === ' ') {
													e.preventDefault();
													handleAgentClick(item.agentId);
												}
											}}
										>
											<Avatar 
												src={item.avatarUrl}
												type={item.avatarType as any}
												fallback={item.player}
											/>
											<div className="flex flex-col">
												<span className="font-medium">{item.player}</span>
												{item.is_system && (
													<Badge variant="secondary" className="text-xs w-fit">System Agent</Badge>
												)}
											</div>
										</div>
									)
								},
								...(gameTypeFilter === "all" ? [{
									key: 'game',
									header: 'Game',
									render: (item: any) => (
										<span className="text-sm font-medium">{item.game}</span>
									)
								}] : []),
								{ key: 'games', header: 'Games Played' },
								{ key: 'winrate', header: 'Win Rate' },
								{ 
									key: 'rating', 
									header: 'Rating',
									render: (item) => (
										<span className="font-semibold text-brand-teal">{item.rating}</span>
									)
								},
								...(showWinnings ? [{
									key: 'winnings',
									header: 'Total Winnings',
									render: (item: any) => (
										<Badge variant={item.winnings >= 0 ? "secondary" : "destructive"}>
											${item.winnings.toLocaleString()}
										</Badge>
									)
								}] : []),
							]}
							loading={loading}
							emptyMessage="No leaderboard data available."
						/>
					</div>
				</div>
				</div>
				</div>
			</PageContainer>
			<AgentProfileModal 
				agentId={selectedAgentId}
				open={isProfileOpen}
				onOpenChange={closeAgentProfile}
			/>
		</PageBackground>
	);
}

export default Leaderboard;

