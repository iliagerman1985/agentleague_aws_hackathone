export type GameType = "texas_holdem" | "chess";

export enum GameEnvironment {
  TEXAS_HOLDEM = 'texas_holdem',
  CHESS = 'chess',
}

export type ChessTimeControl = "blitz" | "long";

export interface BaseMatchmakingConfig {
	env: GameType;
	minPlayers: number;
	maxPlayers: number;
}

export interface ChessMatchmakingConfig extends BaseMatchmakingConfig {
	timeControl: ChessTimeControl;
	disableTimers?: boolean;
}

export type MatchmakingConfig = ChessMatchmakingConfig;

