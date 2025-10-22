import React from 'react';
import { SidebarProvider, useSidebar } from '@/contexts/SidebarContext';
import { Sidebar } from './Sidebar';
import { MobileNav } from './MobileNav';
import { Header } from './Header';
import { useAppearance, COLOR_SCHEMES } from "@/contexts/AppearanceContext";

import { cn } from '@/lib/utils';
import { CrtOverlay } from './CrtOverlay';
import { PageTransition } from '@/components/common/layout/PageTransition';
import Particles from '@/components/Particles';

import { FloatingCreditsBubble } from "@/components/common/utility/FloatingCreditsBubble";
import { PurchaseCelebrationOverlay } from "@/components/common/utility/PurchaseCelebrationOverlay";

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayoutContent: React.FC<AppLayoutProps> = ({ children }) => {
  const { isOpen, isMobile } = useSidebar();
  const { backgroundAnimations, colorScheme } = useAppearance();

  // Get theme colors based on current color scheme
  const themeColors = (() => {
    const schemeData = COLOR_SCHEMES.find((cs: any) => cs.id === colorScheme);
    return {
      primary: schemeData?.primary || '#0891B2',
      accent: schemeData?.accent || '#EA580C'
    };
  })();

  return (
    <div className="relative h-[100dvh] bg-background overflow-hidden" data-testid="app-layout">
      {/* Global animated background */}
      {backgroundAnimations && (
        <div className="absolute inset-0" style={{ width: '100%', height: '100%', position: 'absolute', zIndex: 0, opacity: 0.7 }}>
          <Particles
            particleColors={[themeColors.primary, themeColors.accent]}
            particleCount={200}
            particleSpread={15}
            speed={0.2}
            particleBaseSize={200}
            moveParticlesOnHover={true}
            alphaParticles={false}
            disableRotation={false}
          />
        </div>
      )}
      {/* CRT overlay for subtle retro feel */}
      <CrtOverlay />

      {/* Fixed Header */}
      <Header data-testid="app-header" />
      {/* One-shot celebration overlay after successful purchase */}
      <PurchaseCelebrationOverlay />

      {/* Desktop Sidebar */}
      {!isMobile && (
        <aside className="fixed left-0 top-0 z-40 h-screen overflow-hidden" data-testid="desktop-sidebar">
          <Sidebar />
        </aside>
      )}

      {/* Mobile Navigation */}
      {isMobile && <MobileNav data-testid="mobile-nav" />}

      {/* Main Content Area */}
      <div
        className={cn(
          "relative z-10 flex flex-col transition-all duration-300",
          "h-[calc(100dvh-3rem)] mt-12 lg:h-[100dvh] lg:mt-0",
          !isMobile && isOpen && "ml-72",
          !isMobile && !isOpen && "ml-20"
        )}
        data-testid="main-content-area"
      >
        {/* Page Content */}
        <main className="flex-1 overflow-y-auto" data-testid="app-main">
          <div className="p-0 sm:p-2 lg:p-3 h-full">
            <PageTransition>
              {children}
            </PageTransition>
          </div>
          <FloatingCreditsBubble data-testid="floating-credits-bubble" />
        </main>
      </div>
    </div>
  );
};

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <SidebarProvider>
      <AppLayoutContent>{children}</AppLayoutContent>
    </SidebarProvider>
  );
};
