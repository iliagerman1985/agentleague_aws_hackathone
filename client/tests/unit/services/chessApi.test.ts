/// <reference types="vitest" />

import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("@/lib/api", () => {
  return {
    api: {
      post: vi.fn(),
      get: vi.fn(),
    },
  };
});

import { api } from "@/lib/api";
import { ChessApiService } from "@/services/chessApi";
import type { GameId, PlayerId } from "@/types/ids";
import type { TurnResultResponse } from "@/services/chessApi";

describe("ChessApiService.finalizeTimeout", () => {
  const gameId = "game-123" as GameId;
  const playerId = "player-abc" as PlayerId;

  const response: TurnResultResponse = {
    gameId,
    newState: {} as any,
    newEvents: [],
    isFinished: true,
    currentPlayerId: null,
  };

  beforeEach(() => {
    vi.mocked(api.post).mockReset();
  });

  it("POSTs to the timeout endpoint with the expected payload", async () => {
    vi.mocked(api.post).mockResolvedValue(response);

    const result = await ChessApiService.finalizeTimeout(gameId, playerId);

    expect(api.post).toHaveBeenCalledWith(`/api/v1/games/${gameId}/timeout`, { player_id: playerId });
    expect(result).toBe(response);
  });
});
