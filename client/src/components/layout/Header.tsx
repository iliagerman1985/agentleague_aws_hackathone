import React from 'react';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
// ThemeToggle removed for single-theme design
import { useSidebar } from '@/contexts/SidebarContext';


export const Header: React.FC = () => {
  const { toggle } = useSidebar();


  return (
    <header className="fixed top-0 left-0 right-0 z-40 h-12 bg-secondary/95 backdrop-blur supports-[backdrop-filter]:bg-secondary/90 border-b border-border/30 flex items-center justify-between px-1 lg:px-4 lg:hidden shadow-lg shadow-black/10">
      {/* Left side - Mobile menu button (mobile only) */}
      <div className="flex items-center">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggle}
          className="h-12 w-12 p-2 md:hidden"
        >
          <Menu className="!h-7 !w-7" />
          <span className="sr-only">Toggle navigation menu</span>
        </Button>        {/* Breadcrumb or page title could go here */}
        <div className="hidden sm:block">
          <h1 className="text-base font-semibold text-foreground">
            Agent League
          </h1>
        </div>
      </div>

      {/* Right side - reserved (no coin badge) */}
      <div className="flex items-center gap-3 pr-1" />
    </header>
  );
};
