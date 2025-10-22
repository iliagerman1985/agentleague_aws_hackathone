import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { SharedModal } from '@/components/common/SharedModal';
import { DialogFooter } from '@/components/ui/dialog';

import { ConfirmDialog } from '@/components/common';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

import {
  Search,
  Tag,
  Play,
  Trash2,
  Loader2,
  FileText,
  Clock
} from 'lucide-react';
import { api } from '@/lib/api';
import { type TestScenarioResponse } from '@/services/agentsService';
import { GameStatePreview } from '@/components/games/GameStatePreview';
import { GameEnvironment } from '@/services/agentsService';
import { ChessApiService } from '@/services/chessApi';

import type { ChessStateView } from '@/types/chess';

function makeChessPresetTitle(state: ChessStateView): string {
  const pieceValues: Record<string, number> = { pawn: 1, knight: 3, bishop: 3, rook: 5, queen: 9 };
  let white = 0;
  let black = 0;
  for (const row of state.board) {
    for (const cell of row) {
      if (!cell) continue;
      if (cell.type === 'king') continue;
      const val = pieceValues[cell.type] ?? 0;
      if (cell.color === 'white') white += val; else black += val;
    }
  }
  const delta = white - black;
  const side = state.sideToMove === 'white' ? 'White' : 'Black';
  const material = delta === 0 ? 'material equal' : `${delta > 0 ? '+' : ''}${delta}`;
  return `${side} to move • ${material}`;
}


interface SavedStatesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  environment?: GameEnvironment;
  onLoadState?: (gameState: Record<string, any>, description?: string) => void;
}

export const SavedStatesDialog: React.FC<SavedStatesDialogProps> = ({
  open,
  onOpenChange,
  environment,
  onLoadState,
}) => {
  const [savedStates, setSavedStates] = useState<TestScenarioResponse[]>([]);
  const [filteredStates, setFilteredStates] = useState<TestScenarioResponse[]>([]);
  const [selectedState, setSelectedState] = useState<TestScenarioResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  // Valid chess FEN positions for presets
  const CHESS_PRESET_FENS: string[] = [
    "6kr/5p1p/4pPp1/2p1P3/2p1PQ2/4n2P/pp3nPK/7R w - - 0 1",
    "8/pR4pk/1b2p3/2p3p1/N1p5/7P/Pr4P1/6K1 w - - 0 32",
    "8/B7/7P/4p3/3b3k/8/8/2K5 b - - 1 1",
    "8/6kp/6p1/4p3/p3rPRP/3K2P1/8/8 w - - 2 44",
    "r4k1r/1b2bPR1/p4n1B/3p4/4P2P/1q5B/PpP5/1K4R1 b - - 1 26",
    "5rk1/pp4pp/4p3/2R3Q1/3n4/6qr/P1P2PPP/5RK1 w - - 2 24",
    "8/8/4kpp1/3p4/p6P/2B4b/6P1/6K1 w - - 1 48",
  ];

  const [isChessAgent, setIsChessAgent] = useState(false);
  const [presetPreviews, setPresetPreviews] = useState(
    CHESS_PRESET_FENS.map((fen, i) => ({ id: i + 1, name: 'Loading…', fen, jsonText: null as string | null, loading: true as boolean, error: undefined as string | undefined }))
  );

  const [error, setError] = useState<string | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [stateToDelete, setStateToDelete] = useState<TestScenarioResponse | null>(null);

  // Determine agent environment to conditionally show chess presets
  useEffect(() => {
    if (!open) return;
    // Use environment directly if provided
    if (environment) {
      setIsChessAgent(environment === GameEnvironment.CHESS);
    } else {
      setIsChessAgent(false);
    }
  }, [open, environment]);

  // Load preset previews when dialog opens for chess agents
  useEffect(() => {
    if (!open || !isChessAgent) return;
    CHESS_PRESET_FENS.forEach(async (fen, idx) => {
      try {
        const resp = await ChessApiService.convertFENToState({ fen });
        const state = resp.state as ChessStateView;
        const jsonText = JSON.stringify(state ?? {}, null, 2);
        const title = state ? makeChessPresetTitle(state) : `Position ${idx + 1}`;
        setPresetPreviews(prev => {
          const next = [...prev];
          next[idx] = { ...next[idx], name: title, jsonText, loading: false, error: undefined };
          return next;
        });
      } catch (err: any) {
        console.error(`Failed to load FEN ${idx}:`, err);
        setPresetPreviews(prev => {
          const next = [...prev];
          next[idx] = { ...next[idx], loading: false, error: 'Invalid position' };
          return next;
        });
      }
    });
  }, [open, isChessAgent]);

  // Load saved states when dialog opens
  useEffect(() => {
    if (open) {
      loadSavedStates();
    }
  }, [open, environment]);

  // Filter states based on search and tags
  useEffect(() => {
    let filtered = savedStates;

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(state =>
        state.name.toLowerCase().includes(query) ||
        (state.description && state.description.toLowerCase().includes(query))
      );
    }

    // Apply tag filter
    if (selectedTags.length > 0) {
      filtered = filtered.filter(state =>
        selectedTags.some(tag => state.tags.includes(tag))
      );
    }

    setFilteredStates(filtered);
  }, [savedStates, searchQuery, selectedTags]);

  const loadSavedStates = async () => {
    setLoading(true);
    setError(null);

    try {
      let states;
      if (environment) {
        // Load states by environment
        states = await api.agents.getTestScenarios({ environment });
      } else {
        // No filter - load all states
        states = await api.agents.getTestScenarios();
      }
      setSavedStates(states);
      setSelectedState(states[0] || null);
    } catch (err: any) {
      console.error('Failed to load saved states:', err);
      setError(err.message || 'Failed to load saved states');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadState = () => {
    if (selectedState && onLoadState) {
      onLoadState(selectedState.gameState, selectedState.description || undefined);
      onOpenChange(false);
    }
  };

  const handleDeleteState = async () => {
    if (!stateToDelete) return;

    try {
      await api.agents.deleteTestScenario(stateToDelete.id);
      setSavedStates(prev => prev.filter(state => state.id !== stateToDelete.id));
      if (selectedState?.id === stateToDelete.id) {
        setSelectedState(null);
      }
      setDeleteConfirmOpen(false);
      setStateToDelete(null);
    } catch (err: any) {
      console.error('Failed to delete state:', err);
      setError(err.message || 'Failed to delete state');
    }
  };

  const handleTagToggle = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

  // Get all unique tags from saved states
  const allTags = Array.from(new Set(savedStates.flatMap(state => state.tags))).sort();

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <>
      <SharedModal
        open={open}
        onOpenChange={onOpenChange}
        title="Saved Game States"
        size="2xl"
        className="h-[80vh]"
        contentClassName="flex flex-col"
      >

          <div className={`flex-1 grid gap-6 min-h-0 ${isChessAgent ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-3'}`}>
            {/* Left Panel - List and Filters */}
            <div className={`${isChessAgent ? '' : 'lg:col-span-2'} flex flex-col min-h-0`}>
              {/* Search and Filters */}
              <div className="space-y-4 mb-4">
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search saved states..."
                    className="pl-10"
                  />
                </div>

                {/* Tag Filters */}
                {allTags.length > 0 && (
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">Filter by tags:</Label>
                    <div className="flex flex-wrap gap-2">
                      {allTags.map((tag) => (
                        <Badge
                          key={tag}
                          variant={selectedTags.includes(tag) ? "default" : "outline"}
                          className="cursor-pointer hover:bg-primary/80"
                          onClick={() => handleTagToggle(tag)}
                        >
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Chess Presets (only for chess agents) */}
              {isChessAgent && (
                <div className="mb-4 space-y-2">
                  <Label className="text-sm font-medium">Predefined Chess Positions</Label>
                  <div className="max-h-[55vh] overflow-y-auto pr-1">
                    <div className="grid grid-cols-1 gap-3">
                      {presetPreviews.map((p) => (
                        <Card key={p.id} className="p-4 bg-card/80 backdrop-blur-sm">
                          <div className="flex flex-col gap-3">
                            {/* Chess board preview with better visibility */}
                            <div className="w-full aspect-square rounded-lg overflow-hidden bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-900 p-2 border-2 border-border">
                              {p.jsonText ? (
                                <GameStatePreview
                                  environment={GameEnvironment.CHESS}
                                  jsonText={p.jsonText}
                                  hideCapturedPieces={true}
                                />
                              ) : (
                                <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                                  {p.loading ? 'Loading…' : (p.error || 'Error')}
                                </div>
                              )}
                            </div>
                            {/* Description and button below the board */}
                            <div className="flex items-center justify-between gap-3">
                              <div className="text-sm font-medium whitespace-pre-wrap break-words flex-1">
                                {p.name}
                              </div>
                              <Button
                                size="sm"
                                variant="brand-accent"
                                onClick={() => {
                                  if (!onLoadState || !p.jsonText) return;
                                  try {
                                    const obj = JSON.parse(p.jsonText);
                                    onLoadState(obj, p.name);
                                    onOpenChange(false);
                                  } catch {}
                                }}
                                disabled={!p.jsonText}
                              >
                                Use
                              </Button>
                            </div>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* States List */}
              <div className="flex-1 border rounded-lg overflow-y-auto">
                {loading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                    <span className="ml-2">Loading saved states...</span>
                  </div>
                ) : error ? (
                  <div className="p-4 text-center text-red-600">
                    <p>{error}</p>
                    <Button variant="outline" size="sm" onClick={loadSavedStates} className="mt-2">
                      Try Again
                    </Button>
                  </div>
                ) : filteredStates.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground">
                    <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-medium mb-2">No saved states found</p>
                    <p className="text-sm">
                      {savedStates.length === 0
                        ? "Save your first game state to get started"
                        : "Try adjusting your search or filters"
                      }
                    </p>
                  </div>
                ) : (
                  <div className="p-2 space-y-2">
                    {filteredStates.map((state) => (
                      <Card
                        key={state.id}
                        className={`p-3 cursor-pointer transition-colors hover:bg-accent ${
                          selectedState?.id === state.id ? 'ring-2 ring-primary' : ''
                        }`}
                        onClick={() => setSelectedState(state)}
                      >
                        <div className="flex items-start justify-between pr-3">
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium truncate">{state.name}</h4>
                            {state.description && (
                              <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">
                                {state.description}
                              </p>
                            )}
                            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                              <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {formatDate(state.createdAt)}
                              </div>
                              {state.tags.length > 0 && (
                                <div className="flex items-center gap-1">
                                  <Tag className="h-3 w-3" />
                                  {state.tags.length} tag{state.tags.length !== 1 ? 's' : ''}
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="flex gap-1 ml-2">
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    aria-label="Delete saved state"
                                    variant="destructive"
                                    size="icon"
                                    className="rounded-full"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setStateToDelete(state);
                                      setDeleteConfirmOpen(true);
                                    }}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Delete</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Panel - Preview (hidden for chess presets to maximize width) */}
            {!isChessAgent && (
              <div className="flex flex-col min-h-0">
                {selectedState ? (
                  <div className="flex flex-col h-full">
                    <div className="mb-4">
                      <h3 className="font-semibold text-lg mb-2">{selectedState.name}</h3>
                      {selectedState.description && (
                        <p className="text-sm text-muted-foreground mb-3">
                          {selectedState.description}
                        </p>
                      )}
                      {selectedState.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-3">
                          {selectedState.tags.map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                      <p className="text-xs text-muted-foreground">
                        Created: {formatDate(selectedState.createdAt)}
                      </p>
                    </div>

                    <div className="flex-1 min-h-0">
                      <Label className="text-sm font-medium mb-2 block">Game State:</Label>
                      <div className="h-full border rounded-lg overflow-y-auto">
                        <pre className="p-3 text-xs whitespace-pre-wrap">
                          {JSON.stringify(selectedState.gameState, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-muted-foreground">
                    <div className="text-center">
                      <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Select a saved state to preview</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleLoadState}
              disabled={!selectedState}
              className="flex items-center gap-2"
            >
              <Play className="h-4 w-4" />
              Load State
            </Button>
          </DialogFooter>
      </SharedModal>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title="Delete Saved State"
        description={`Are you sure you want to delete "${stateToDelete?.name}"? This action cannot be undone.`}
        onConfirm={handleDeleteState}
      />
    </>
  );
};
