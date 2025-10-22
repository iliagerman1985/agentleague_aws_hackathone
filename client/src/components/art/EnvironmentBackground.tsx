/**
 * Environment-aware background component
 * Automatically selects the appropriate background art based on environment
 */

import React from "react";
import { ChessBackground } from "./ChessBackground";
import { PokerBackground } from "./PokerBackground";
import { TrophiesBackground } from "./TrophiesBackground";
import { GamesBackground } from "./GamesBackground";
import { AgentsBackground } from "./AgentsBackground";
import { ToolsBackground } from "./ToolsBackground";
import { TestsBackground } from "./TestsBackground";
import { HelpBackground } from "./HelpBackground";
import { GenericBackground } from "./GenericBackground";

interface EnvironmentBackgroundProps {
  environment?: string;
  className?: string;
  opacity?: number;
  variant?: "geometric" | "dots" | "waves" | "grid";
}

export const EnvironmentBackground: React.FC<EnvironmentBackgroundProps> = ({
  environment,
  className,
  opacity = 0.03,
  variant = "geometric"
}) => {
  const normalizedEnv = environment?.toLowerCase();

  if (normalizedEnv === "chess") {
    return <ChessBackground className={className} opacity={opacity} />;
  }

  if (normalizedEnv === "texas_holdem") {
    return <PokerBackground className={className} opacity={opacity} />;
  }

  if (normalizedEnv === "leaderboard") {
    return <TrophiesBackground className={className} opacity={opacity} />;
  }

  if (normalizedEnv === "games") {
    return <GamesBackground className={className} opacity={opacity} />;
  }

  if (normalizedEnv === "agents") {
    return <AgentsBackground className={className} opacity={opacity} />;
  }

  if (normalizedEnv === "tools") {
    return <ToolsBackground className={className} opacity={opacity} />;
  }

  if (normalizedEnv === "tests") {
    return <TestsBackground className={className} opacity={opacity} />;
  }

  if (normalizedEnv === "help") {
    return <HelpBackground className={className} opacity={opacity} />;
  }

  return <GenericBackground className={className} opacity={opacity} variant={variant} />;
};

