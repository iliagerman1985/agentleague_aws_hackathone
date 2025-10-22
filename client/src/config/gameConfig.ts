/**
 * Central game configuration - single source of truth for all game metadata
 */

import { Spade, Crown, MapPin, Home, DollarSign, Swords } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type GameStatus = 'available' | 'coming_soon';

export interface GameConfig {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
  iconColor: string;
  status: GameStatus;
  features: string[];
  maxPlayers: number;
  estimatedTime: string;
  href?: string;
  image: string;
}

/**
 * All game configurations
 * This is the single source of truth for game metadata across the application
 */
export const GAME_CONFIGS: Record<string, GameConfig> = {
  texas_holdem: {
    id: 'texas_holdem',
    title: 'Texas Hold\'em Poker',
    description: 'Classic poker game with community cards and strategic betting rounds.',
    icon: Spade,
    iconColor: 'text-red-500',
    status: 'coming_soon',
    features: ['AI Agents', 'Real-time Play', 'Multiple Betting Rounds', 'Tournament Mode'],
    maxPlayers: 5,
    estimatedTime: '15-30 min',
    href: '/games/texas-holdem',
    image: '/games/poker.png'
  },
  chess: {
    id: 'chess',
    title: 'Chess',
    description: 'Classic two-player strategy. Play blitz or long with perfect information.',
    icon: Crown,
    iconColor: 'text-yellow-500',
    status: 'available',
    features: ['Blitz or Long clocks', 'Agent move option', 'Event log', 'Legal move validation'],
    maxPlayers: 2,
    estimatedTime: '10–20 min',
    href: '/games/chess',
    image: '/games/chess.png'
  },
  risk: {
    id: 'risk',
    title: 'Risk',
    description: 'Strategic conquest game of global domination with armies and territories.',
    icon: MapPin,
    iconColor: 'text-blue-500',
    status: 'coming_soon',
    features: ['Territory Control', 'Strategic Planning', 'Dice Combat', 'Alliance System'],
    maxPlayers: 6,
    estimatedTime: '60-120 min',
    image: '/games/risk.png'
  },
  catan: {
    id: 'catan',
    title: 'Catan',
    description: 'Build settlements, trade resources, and become the dominant force on the island.',
    icon: Home,
    iconColor: 'text-green-500',
    status: 'coming_soon',
    features: ['Resource Trading', 'Settlement Building', 'Development Cards', 'Longest Road'],
    maxPlayers: 4,
    estimatedTime: '45-90 min',
    image: '/games/catan.png'
  },
  monopoly: {
    id: 'monopoly',
    title: 'Monopoly',
    description: 'Buy, sell, and trade properties to bankrupt your opponents in this classic game.',
    icon: DollarSign,
    iconColor: 'text-emerald-500',
    status: 'coming_soon',
    features: ['Property Trading', 'Auctions', 'Chance & Community Chest', 'Houses & Hotels'],
    maxPlayers: 6,
    estimatedTime: '60-180 min',
    image: '/games/monopoly.png'
  },
  tanks: {
    id: 'tanks',
    title: 'Tanks',
    description: 'Tactical tank warfare with strategic movement and combat positioning.',
    icon: Swords,
    iconColor: 'text-orange-500',
    status: 'coming_soon',
    features: ['Real-time Combat', 'Strategic Movement', 'Power-ups', 'Team Battles'],
    maxPlayers: 8,
    estimatedTime: '10-20 min',
    image: '/games/tanks.png'
  }
};

/**
 * Get all games as an array
 */
export const getAllGames = (): GameConfig[] => {
  return Object.values(GAME_CONFIGS);
};

/**
 * Get a specific game config by ID
 */
export const getGameConfig = (gameId: string): GameConfig | undefined => {
  return GAME_CONFIGS[gameId];
};

/**
 * Get all available games
 */
export const getAvailableGames = (): GameConfig[] => {
  return getAllGames().filter(game => game.status === 'available');
};

/**
 * Get all coming soon games
 */
export const getComingSoonGames = (): GameConfig[] => {
  return getAllGames().filter(game => game.status === 'coming_soon');
};

