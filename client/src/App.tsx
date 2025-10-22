import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import { AppearanceProvider } from '@/contexts/AppearanceContext';
import { AvatarProvider } from '@/contexts/AvatarContext';
import { LLMProvider } from '@/contexts/LLMContext';
import { UiSettingsProvider } from '@/contexts/UiSettingsContext';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { ToastProvider } from '@/components/common/notifications/ToastProvider';
import { LoginForm } from '@/components/auth/LoginForm';
import { RegisterForm } from '@/components/auth/RegisterForm';
import { ConfirmSignUpForm } from '@/components/auth/ConfirmSignUpForm';
import { OAuthCallback } from '@/components/auth/OAuthCallback';
import { AppLayout } from '@/components/layout/AppLayout';
import AgentManagementPage from '@/components/pages/agents/AgentManagementPage';
import Games from '@/components/pages/Games';
import Leaderboard from '@/components/pages/Leaderboard';
import { Settings } from '@/components/pages/Settings';
import { Help } from '@/components/pages/Help';
import { HelpDetailPage } from '@/components/pages/help/HelpDetailPage';

import ToolEditorPage from '@/components/pages/tools/ToolEditorPage';
import AgentEditorPage from '@/components/pages/agents/AgentEditorPage';
import PokerGame from '@/pages/PokerGame';
import { ChessGame } from '@/pages/ChessGame';
import { GameReplayPage } from '@/pages/GameReplayPage';
import { BillingResult } from '@/components/pages/BillingResult';
import TestEditorPage from '@/components/pages/tests/TestEditorPage';
import GamesManagement from '@/components/pages/GamesManagement';

function App() {
  return (
    <AppearanceProvider>
      <AuthProvider>
        <AvatarProvider>
          <LLMProvider>
            <UiSettingsProvider>
              <ToastProvider>
              <Router>
                <div className="h-screen bg-background text-foreground">
                  <Routes>
                    {/* Public routes (redirect to Home if authenticated) */}
                    <Route
                      path="/login"
                      element={
                        <ProtectedRoute requireAuth={false}>
                          <LoginForm />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/register"
                      element={
                        <ProtectedRoute requireAuth={false}>
                          <RegisterForm />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/confirm-signup"
                      element={
                        <ProtectedRoute requireAuth={false}>
                          <ConfirmSignUpForm />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/auth/callback"
                      element={
                        <ProtectedRoute requireAuth={false}>
                          <OAuthCallback />
                        </ProtectedRoute>
                      }
                    />

                    {/* Protected routes with layout */}
                    <Route
                      path="/agents"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <AgentManagementPage />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/agents/new"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <AgentEditorPage />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/agents/:id"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <AgentEditorPage />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/games"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <GamesManagement />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/games/select"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <Games />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/games-management"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <GamesManagement />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/leaderboard"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <Leaderboard />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/tools"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <AgentManagementPage />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/tools/new"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <ToolEditorPage />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/tools/:id"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <ToolEditorPage />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/tests"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <AgentManagementPage />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/tests/new"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <TestEditorPage />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/tests/:id"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <TestEditorPage />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />

                    <Route
                      path="/settings"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <Settings />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/help"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <Help />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/help/:topicId"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <HelpDetailPage />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />

                    {/* Texas Hold'em Game Routes */}
                    <Route
                      path="/games/texas-holdem"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <PokerGame />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/games/texas-holdem/:gameId"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <PokerGame />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    {/* Generic game replay route - must come before specific game routes */}
                    <Route
                      path="/games/:gameType/:gameId/replay"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <GameReplayPage />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />

                    {/* Chess Game Routes */}
                    <Route
                      path="/games/chess"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <ChessGame />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/games/chess/:gameId"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <ChessGame />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />

                    {/* Billing result routes */}
                    <Route
                      path="/billing/success"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <BillingResult />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/billing/cancel"
                      element={
                        <ProtectedRoute>
                          <AppLayout>
                            <BillingResult />
                          </AppLayout>
                        </ProtectedRoute>
                      }
                    />

                    {/* Default redirects */}
                    <Route path="/" element={<Navigate to="/games-management" replace />} />
                    <Route path="*" element={<Navigate to="/games-management" replace />} />
                  </Routes>
                </div>
              </Router>
            </ToastProvider>
            </UiSettingsProvider>
          </LLMProvider>
        </AvatarProvider>
      </AuthProvider>
    </AppearanceProvider>
  );
}

export default App;
