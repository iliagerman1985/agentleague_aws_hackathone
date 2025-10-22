import React, { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { ColorSchemeSelector } from "@/components/ui/color-scheme-selector";
import { useAuth } from "@/contexts/AuthContext";
import { useAppearance } from "@/contexts/AppearanceContext";
import { useAvatar } from "@/contexts/AvatarContext";
import { Switch } from "@/components/ui/switch";
import { LLMIntegrationDialog } from "@/components/llm/LLMIntegrationDialog";
import { ProviderIcon } from "@/components/llm/ProviderIcon";
import { useLLM } from "@/contexts/LLMContext";
import { PageBackground } from "@/components/common/layout/PageBackground";
import { PasswordChangeDialog } from "@/components/auth/PasswordChangeDialog";
import { DeleteAccountDialog } from "@/components/auth/DeleteAccountDialog";
import { AvatarUpload } from "@/components/common/AvatarUpload";
import { User, KeyRound, Mail, IdCard, Bot, Gamepad2, Wrench, CalendarClock, Trash2 } from "lucide-react";
import { api, type LLMIntegrationResponse } from "@/lib/api";
import { useToasts } from "@/components/common/notifications/ToastProvider";
import { type LLMIntegrationId } from "@/types/ids";
import { ConfirmDialog } from "@/components/common/dialogs/ConfirmDialog";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { cn } from "@/lib/utils";

// Simple SVG coin stack icon with warm gradient - same as dialog
const CoinStackIcon = ({ className = "" }: { className?: string }) => (
  <svg viewBox="0 0 64 64" className={className} aria-hidden>
    <defs>
      <linearGradient id="coinGradSettings" x1="0" x2="1">
        <stop stopColor="#FDE68A" />
        <stop offset="1" stopColor="#F59E0B" />
      </linearGradient>
    </defs>
    <ellipse cx="32" cy="18" rx="18" ry="8" fill="url(#coinGradSettings)" stroke="#A16207" />
    <ellipse cx="32" cy="28" rx="18" ry="8" fill="url(#coinGradSettings)" stroke="#A16207" />
    <ellipse cx="32" cy="38" rx="18" ry="8" fill="url(#coinGradSettings)" stroke="#A16207" />
  </svg>
);

// Auto-fit number text to available width by shrinking font size between min/max
function AutoFitNumber({
  value,
  className = "",
  maxPx = 32,
  minPx = 14,
}: {
  value: string | number;
  className?: string;
  maxPx?: number;
  minPx?: number;
}) {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const textRef = React.useRef<HTMLSpanElement | null>(null);

  const fit = React.useCallback(() => {
    const container = containerRef.current;
    const text = textRef.current;
    if (!container || !text) return;

    // Start from max each run, then shrink until it fits or we hit the min
    let size = maxPx;
    text.style.fontSize = `${size}px`;

    // guard to avoid infinite loops
    let safety = 0;
    while (text.scrollWidth + 3 > container.clientWidth && size > minPx && safety < 40) {
      size -= 1;
      text.style.fontSize = `${size}px`;
      safety += 1;
    }
  }, [maxPx, minPx, value]);

  React.useLayoutEffect(() => {
    fit();
    const ro = new ResizeObserver(() => fit());
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [fit]);

  return (
    <div ref={containerRef} className="ml-3 flex-1 min-w-0 text-right pr-1 sm:pr-1.5">
      <span ref={textRef} className={className} style={{ fontSize: `${maxPx}px`, display: "inline-block", whiteSpace: "nowrap" }}>
        {value}
      </span>
    </div>
  );
}


const DevErrorTrigger: React.FC = () => {
  if (!import.meta.env.DEV) {
    return null;
  }

  const [shouldThrow, setShouldThrow] = useState(false);

  const triggerError = useCallback(() => {
    setShouldThrow(true);
  }, []);

  if (shouldThrow) {
    throw new Error("Intentional development error for previewing the ErrorBoundary.");
  }

  return (
    <div className="rounded-2xl border border-dashed border-brand-accentOrange/50 bg-brand-accentOrange/10 p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-accentOrange/80">
            Development helper
          </p>
          <p className="mt-1 text-sm text-brand-accentOrange/90">
            Click the button to throw a controlled error and render the global ErrorBoundary. Available in development only.
          </p>
        </div>
        <Button
          onClick={triggerError}
          className="flex items-center justify-center gap-2 rounded-lg bg-brand-accentOrange text-white shadow-md shadow-brand-accentOrange/40 transition hover:bg-brand-accentOrange/90"
        >
          Trigger ErrorBoundary
        </Button>
      </div>
    </div>
  );
};





// Coin bundle type for rendering and API typing
interface Bundle {
  id: string;
  name: string;
  coins: number;
  currency: string;
  amount_cents: number;
  price_id?: string;
}

export const Settings: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const { backgroundAnimations, setBackgroundAnimations } = useAppearance();
  const { userAvatar, isLoading: avatarLoading, uploadAvatar, removeAvatar } = useAvatar();
  const { integrations, refreshIntegrations } = useLLM();
  const [llmDialogOpen, setLlmDialogOpen] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [deleteAccountDialogOpen, setDeleteAccountDialogOpen] = useState(false);
  const { push } = useToasts();
  const [settingDefaultId, setSettingDefaultId] = useState<LLMIntegrationId | null>(null);
  const [deletingId, setDeletingId] = useState<LLMIntegrationId | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteCandidate, setDeleteCandidate] = useState<LLMIntegrationResponse | null>(null);


  const handleSetDefaultProvider = async (id: LLMIntegrationId) => {
    setSettingDefaultId(id);
    try {
      await api.llmIntegrations.setDefault(id);
      push({ title: "Success", message: "Default provider updated", tone: "success" });
      await refreshIntegrations();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to set default";
      push({ title: "Error", message: msg, tone: "error" });
    } finally {
      setSettingDefaultId(null);
    }
  };

  const openDeleteConfirm = (integration: LLMIntegrationResponse) => {
    setDeleteCandidate(integration);
    setDeleteConfirmOpen(true);
  };

  const handleDeleteIntegration = async (id: LLMIntegrationId) => {
    setDeletingId(id);
    try {
      await api.llmIntegrations.delete(id);
      push({ title: "Deleted", message: "Integration deleted", tone: "success" });
      await refreshIntegrations();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to delete integration";
      push({ title: "Error", message: msg, tone: "error" });
    } finally {
      setDeletingId(null);
      setDeleteConfirmOpen(false);
      setDeleteCandidate(null);
    }
  };

  // Quick stats
  const [agentCount, setAgentCount] = useState<number>(0);
  const [toolCount, setToolCount] = useState<number>(0);
  const [gamesCount, setGamesCount] = useState<number>(0);

  // Coin bundles for purchase
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [buyingId, setBuyingId] = useState<string | null>(null);
  const [editingNickname, setEditingNickname] = useState<string | undefined>(undefined);
  const [savingProfile, setSavingProfile] = useState(false);


  // Friendly provider name mapping for Settings list
  const getProviderName = (provider: string): string => {
    switch (provider) {
      case "openai": return "OpenAI";
      case "anthropic": return "Anthropic";
      case "google": return "Google";
      case "aws_bedrock": return "AWS Bedrock";
      default: return provider;
    }
  };

  // Robust counter for various API response shapes
  const countItems = (res: any): number => {
    if (Array.isArray(res)) return res.length;
    if (Array.isArray(res?.items)) return res.items.length;
    if (Array.isArray(res?.data)) return res.data.length;
    if (typeof res?.total === "number") return res.total;
    if (typeof res?.count === "number") return res.count;
    return 0;
  };

  useEffect(() => {
    const load = async () => {
      try {
        // Refresh user data to get latest balance
        await refreshUser();

        const [agents, tools, gamesCountResp] = await Promise.all([
          api.get('/api/v1/agents', { timeout: 60000 }),
          api.get('/api/v1/tools', { timeout: 60000 }),
          api.get('/api/v1/games/count?only_active=false', { timeout: 60000 }),
        ]);
        setAgentCount(countItems(agents));
        setToolCount(countItems(tools));
        setGamesCount(typeof gamesCountResp?.count === "number" ? gamesCountResp.count : countItems(gamesCountResp));
      } catch (e) {
        console.warn("Failed to load quick stats", e);
      }
    };
    load();
  }, []);

  // Initialize nickname editor from user
  useEffect(() => {
    setEditingNickname(user?.nickname ?? undefined);
  }, [user?.nickname]);

  // Load available coin bundles on mount
  useEffect(() => {
    (async () => {
      try {
        const resp = await api.billing.listBundles();
        setBundles(resp.bundles ?? []);
      } catch (e) {
        console.warn("Failed to load coin bundles", e);
      }
    })();
  }, []);

  const handleBuy = async (bundleId: string) => {
    setBuyingId(bundleId);
    try {
      const { checkout_url } = await api.billing.createCheckoutSession(bundleId);
      try { sessionStorage.setItem("preCheckoutPath", window.location.pathname + window.location.search); } catch {}
      window.location.href = checkout_url;
    } catch (e) {
      console.error("Failed to start checkout", e);
    } finally {
      setBuyingId(null);
    }
  };

  const handleAvatarUpload = async (
    file: File,
    cropData?: { x: number; y: number; size: number; scale: number }
  ) => {
    try {
      await uploadAvatar(file, 'user', cropData);
      // Avatar context already refreshes user data
      push({ title: "Success", message: "Avatar updated successfully", tone: "success" });
    } catch (e) {
      console.error("Failed to upload avatar", e);
      const msg = e instanceof Error ? e.message : "Failed to upload avatar";
      push({ title: "Error", message: msg, tone: "error" });
    }
  };

  const handleAvatarRemove = async () => {
    try {
      await removeAvatar('user');
      // Refresh user data to get the updated avatar
      refreshUser();
      push({ title: "Success", message: "Avatar reset successfully", tone: "success" });
    } catch (e) {
      console.error("Failed to reset avatar", e);
      const msg = e instanceof Error ? e.message : "Failed to reset avatar";
      push({ title: "Error", message: msg, tone: "error" });
    }
  };

  const memberSince = React.useMemo(() => {
    if (integrations && integrations.length > 0) {
      const minTs = Math.min(
        ...integrations
          .map(i => Date.parse(i.createdAt))
          .filter(n => !Number.isNaN(n))
      );
      if (minTs && Number.isFinite(minTs)) {
        return new Date(minTs).toLocaleDateString();
      }
    }
    return null;
  }, [integrations]);

  const accountCreated = React.useMemo(() => {
    if (user?.createdAt) {
      const parsed = Date.parse(user.createdAt);
      if (!Number.isNaN(parsed)) {
        return new Date(parsed).toLocaleDateString();
      }
    }
    return memberSince;
  }, [user?.createdAt, memberSince]);


  const formatCoins = React.useCallback((n: number) => new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(n), []);

  const accountStats = React.useMemo(() => ([
    {
      key: "bots",
      label: "Bots",
      value: agentCount,
      icon: Bot,
      badgeClass: "bg-brand-teal/15 text-brand-teal",
    },
    {
      key: "games",
      label: "Games Played",
      value: gamesCount,
      icon: Gamepad2,
      badgeClass: "bg-brand-orange/15 text-brand-orange",
    },
    {
      key: "tools",
      label: "Tools",
      value: toolCount,
      icon: Wrench,
      badgeClass: "bg-brand-mint/20 text-brand-mint",
    },
    {
      key: "balance",
      label: "Balance",
      value: formatCoins(user?.coinsBalance ?? 0),
      icon: CoinStackIcon,
      badgeClass: "bg-amber-100 text-amber-600",
    },
  ]), [agentCount, gamesCount, toolCount, user?.coinsBalance, formatCoins]);

  return (
    <PageBackground variant="grid" className="h-full overflow-y-auto">
      <div className="w-full space-y-8 p-6 lg:p-8" data-testid="settings-page">
        <div className="w-full max-w-[95rem] mx-auto space-y-8 pb-8">
        <div className="relative flex items-center justify-between mb-8 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6" data-testid="settings-header">
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
            <EnvironmentBackground environment="settings" opacity={0.20} variant="grid" />
          </div>
          <div className="relative z-10">
            <h1 className="text-2xl sm:text-4xl font-bold text-foreground mb-0 sm:mb-2 truncate max-w-[70vw] sm:max-w-none sm:whitespace-normal" data-testid="settings-title">Settings</h1>
            <p className="hidden sm:block text-muted-foreground text-lg" data-testid="settings-subtitle">Manage your account settings and preferences</p>
          </div>
        </div>

        <DevErrorTrigger />

      <div className="grid grid-cols-1 gap-6 items-start lg:grid-cols-2 grid-flow-row-dense">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 text-sm font-semibold text-brand-teal uppercase">
              <User className="h-4 w-4" />
              Account Settings
            </div>
            <CardDescription>Update your personal information and avatar.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Avatar inside Account Settings */}
            <div className="w-full flex justify-center">
              <AvatarUpload
                currentAvatar={userAvatar.avatarUrl}
                onUpload={handleAvatarUpload}
                onRemove={userAvatar.avatarUrl ? handleAvatarRemove : undefined}
                canRemove={Boolean(userAvatar.avatarUrl)}
                uploading={avatarLoading}
                fallback={user?.fullName || user?.username || "User"}
                size="5xl"
                showBorder
                type={userAvatar.avatarType as any}
                showHelperText={false}
                showCameraButton={true}
              />
            </div>

            {/* Account Info */}
            <div className="flex flex-col gap-6">
              {/* Account Info Cards */}
              <div className="flex flex-col gap-3 flex-1 min-w-0">
                <div className="rounded-lg border border-border/60 bg-card p-4">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                    <Mail className="h-3.5 w-3.5 text-brand-teal" />
                    Email
                  </div>
                  <p className="break-all text-base font-medium text-foreground">{user?.email ?? "—"}</p>
                </div>
                <div className="grid grid-cols-1 gap-3 flex-1">
                  <div className="rounded-lg border border-border/60 bg-card p-4 flex flex-col">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                      <IdCard className="h-3.5 w-3.5 text-brand-teal" />
                      Full Name

                    </div>
                    <p className="break-words text-base font-medium text-foreground flex-1">{user?.fullName || "Not provided"}</p>
                  </div>
                  <div className="rounded-lg border border-border/60 bg-card p-4 flex flex-col">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                      <IdCard className="h-3.5 w-3.5 text-brand-teal" />
                      Nickname

                    </div>
                    <div className="flex items-center gap-3">
                      <input
                        aria-label="Nickname"
                        value={editingNickname ?? ""}
                        onChange={(e) => setEditingNickname(e.target.value)}
                        className="w-full rounded-md border border-border/50 bg-card px-3 py-2 text-sm text-foreground"
                        placeholder="Display name (optional)"
                      />
                      <Button
                        size="sm"
                        onClick={async () => {
                          setSavingProfile(true);
                          try {
                            await api.auth.updateCurrentUser({ nickname: editingNickname ?? null });
                            push({ title: 'Saved', message: 'Profile updated', tone: 'success' });
                            await refreshUser();
                          } catch (e) {
                            const msg = e instanceof Error ? e.message : 'Failed to update profile';
                            push({ title: 'Error', message: msg, tone: 'error' });
                          } finally {
                            setSavingProfile(false);
                          }
                        }}
                        disabled={savingProfile}
                      >
                        {savingProfile ? 'Saving...' : 'Save'}
                      </Button>
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/60 bg-card p-4 flex flex-col">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                      <CalendarClock className="h-3.5 w-3.5 text-brand-teal" />
                      Account Created
                    </div>
                    <p className="text-base font-medium text-foreground flex-1">{accountCreated ?? "—"}</p>
                  </div>
                </div>
                <Button
                  variant="brand-accent"
                  className="w-full justify-center gap-2 h-11"
                  onClick={() => setPasswordDialogOpen(true)}
                >
                  <KeyRound className="h-4 w-4" />
                  Change Password
                </Button>
              </div>
            </div>

            {/* Account Stats */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {accountStats.map(({ key, label, value, icon: Icon, badgeClass }) => (
                <div key={key} className="rounded-lg border border-border/60 bg-card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className={cn("flex h-10 w-10 items-center justify-center rounded-lg shrink-0", badgeClass)}>
                      <Icon className="h-5 w-5" />
                    </span>
                    {key === "balance" ? (
                      <AutoFitNumber
                        value={String(value)}
                        className="block font-bold text-foreground tabular-nums tracking-tight leading-tight"
                        maxPx={32}
                        minPx={12}
                      />
                    ) : (
                      <div className="ml-3 flex-1 min-w-0 text-right">
                        <span className="text-3xl font-bold text-foreground">{value}</span>
                      </div>
                    )}
                  </div>
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:row-span-2">
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>Customize how the application looks</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-foreground">Theme</label>
                <p className="text-sm text-muted-foreground">Choose your preferred theme</p>
              </div>

              <ThemeToggle />
            </div>

            <div className="border-t pt-6">
              <ColorSchemeSelector />
            </div>

            <div className="flex items-center justify-between border-t pt-6">
              <div>
                <label className="text-sm font-medium text-foreground">Background Animations</label>
                <p className="text-sm text-muted-foreground">Enable or disable background animations</p>
              </div>
              <Switch
                checked={backgroundAnimations}
                onCheckedChange={setBackgroundAnimations}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>LLM Providers</CardTitle>
            <CardDescription>Connect and manage your LLM provider integrations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              {integrations.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-sm text-muted-foreground mb-4">No providers connected yet.</p>
                  <Button variant="brand-accent" onClick={() => setLlmDialogOpen(true)}>
                    Add Provider
                  </Button>
                </div>
              ) : (
                <>
                  {integrations.map((i) => (
                    <div
                      key={i.id}
                      className="flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-card px-4 py-3"
                    >
                      {/* Left: icon + name */}
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <ProviderIcon provider={i.provider} size={18} />
                        <span className="text-sm font-medium truncate">{i.displayName || getProviderName(i.provider)}</span>
                        {i.isDefault && (
                          <Badge variant="outline" className="ml-2 text-xs bg-brand-teal/10 text-brand-teal border-brand-teal/30">
                            Default
                          </Badge>
                        )}
                      </div>

                      {/* Right: actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        {!i.isDefault && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleSetDefaultProvider(i.id)}
                            disabled={settingDefaultId === i.id}
                            className="h-8 px-3 text-xs"
                          >
                            {settingDefaultId === i.id ? "Setting..." : "Set Default"}
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => openDeleteConfirm(i)}
                          disabled={deletingId === i.id}
                          className="h-8 px-3 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                        >
                          {deletingId === i.id ? "Deleting..." : "Delete"}
                        </Button>
                      </div>
                    </div>
                  ))}
                  <div className="flex justify-center pt-2">
                    <Button variant="brand-accent" onClick={() => setLlmDialogOpen(true)}>
                      Manage Providers
                    </Button>
                  </div>
                </>
              )}
            </div>
            <LLMIntegrationDialog
              open={llmDialogOpen}
              onOpenChange={(open) => {
                setLlmDialogOpen(open);
                if (!open) refreshIntegrations();
              }}
              onIntegrationChange={() => refreshIntegrations()}
            />
          </CardContent>
        </Card>


            {deleteCandidate && (
              <ConfirmDialog
                open={deleteConfirmOpen}
                onOpenChange={setDeleteConfirmOpen}
                title="Delete Integration"
                description={`Are you sure you want to delete ${deleteCandidate.displayName || getProviderName(deleteCandidate.provider)}? This action cannot be undone.`}
                confirmText={deletingId === deleteCandidate.id ? "Deleting..." : "Delete"}
                cancelText="Cancel"
                onConfirm={() => handleDeleteIntegration(deleteCandidate.id)}
              />
            )}

        <Card>
          <CardHeader>
            <CardTitle>Buy Game Coins</CardTitle>
            <CardDescription>Purchase coin bundles to use across the app</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-foreground">Current Balance</label>
                <p className="text-sm text-muted-foreground">{formatCoins(user?.coinsBalance ?? 0)} coins</p>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {bundles.map((b) => (
                <div key={b.id} className="flex items-center justify-between rounded-lg border p-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="grid size-10 place-items-center rounded-md bg-brand-orange/15 text-brand-orange ring-1 ring-brand-orange/30">
                      <CoinStackIcon className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-medium truncate">{b.name}</div>
                      <div className="text-xs text-muted-foreground">{formatCoins(b.coins)} coins</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-semibold">${(b.amount_cents / 100).toFixed(2)}</div>
                    <Button size="sm" variant="brand-accent" onClick={() => handleBuy(b.id)} disabled={buyingId === b.id}>
                      {buyingId === b.id ? "Processing..." : "Buy"}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>


        {/* Danger Zone - separate section */}
        <Card className="border-destructive/40 bg-destructive/5">
          <CardHeader>
            <CardTitle className="text-destructive">Danger Zone</CardTitle>
            <CardDescription>
              Deleting your account will permanently remove all your data. This action cannot be undone.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row items-start gap-4">
              <Button
                variant="destructive"
                className="gap-2"
                onClick={() => setDeleteAccountDialogOpen(true)}
              >
                <Trash2 className="h-4 w-4" />
                Delete Account
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Password Change Dialog */}
        <PasswordChangeDialog
          open={passwordDialogOpen}
          onOpenChange={setPasswordDialogOpen}
        />

        {/* Delete Account Dialog */}
        <DeleteAccountDialog
          open={deleteAccountDialogOpen}
          onOpenChange={setDeleteAccountDialogOpen}
        />

      </div>

        </div>
      </div>
    </PageBackground>
  );
};
