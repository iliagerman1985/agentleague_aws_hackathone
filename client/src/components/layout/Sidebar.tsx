import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LogOut,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Logo } from '@/components/ui/logo';
import { useSidebar } from '@/contexts/SidebarContext';
import { useAuth } from '@/contexts/AuthContext';
import { useAvatar } from '@/contexts/AvatarContext';

import { Avatar } from '@/components/common/Avatar';

import { navItems, NavItem } from './navItems';

interface SidebarProps {
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ className }) => {
  const { isOpen, toggle, isMobile } = useSidebar();
  const { user, signOut } = useAuth();
  const { userAvatar } = useAvatar();
  const location = useLocation();

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (e) {
      console.error("Sign out error:", e);
    }
  };

  const filteredNavItems = navItems.filter(item =>
    !item.adminOnly || user?.role === 'admin'
  );

  const isItemActive = (item: NavItem): boolean => {
    if (location.pathname === item.href) return true;
    if (item.children) {
      return item.children.some(child => location.pathname === child.href);
    }
    return false;
  };

  return (
    <div
      className={cn(
        "relative h-full",
        isOpen ? "w-72" : "w-20",
        className
      )}
    >
      <div className="flex h-[calc(100vh-1rem)] sm:h-[calc(100vh-1.5rem)] flex-col m-2 sm:m-3 rounded-xl bg-secondary sidebar-surface border-2 border-primary shadow-lg shadow-black/20 overflow-hidden">
      {/* Header */}
      <div className="flex h-44 items-center justify-between px-1 border-b border-border/30 bg-secondary sidebar-logo-bg">
        {isOpen ? (
          <Link to="/games-management" className="flex items-center justify-center w-full hover:opacity-80 transition-opacity">
            <Logo width={600} height={170} color="none" className="h-40" />
          </Link>
        ) : (
          <Link to="/games-management" className="flex items-center justify-center w-full hover:opacity-80 transition-opacity">
            <Logo width={400} height={110} color="none" className="h-32" />
          </Link>
        )}
        {!isMobile && isOpen && (
          <Button
            variant="ghost"
            size="icon"
            onClick={toggle}
            className="h-10 w-10 flex-shrink-0"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        )}
        {!isMobile && !isOpen && (
          <Button
            variant="ghost"
            size="icon"
            onClick={toggle}
            className="absolute top-4 right-2 h-8 w-8 z-10"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1.5 p-3 bg-transparent">
        {filteredNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = isItemActive(item);

          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                "sidebar-link group flex items-center gap-3.5 rounded-lg px-3.5 py-2.5 font-medium text-base lg:text-lg transition-all duration-200 ring-1 ring-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
                isActive ? "is-active" : "",
                !isOpen && "justify-center px-2"
              )}
              title={!isOpen ? item.title : undefined}
            >
              <Icon
                className={cn(
                  "h-5 w-5 flex-shrink-0 transition-colors",
                  isActive ? "text-white" : item.iconColor || "text-muted-foreground",
                  !isActive && "group-hover:text-primary"
                )}
              />
              {isOpen && <span className="leading-snug">{item.title}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      {(isOpen || isMobile) && (
        <>
          <Separator />
          <div className="p-4">
            <div className="flex items-center gap-3">
              <Avatar
                src={userAvatar.avatarUrl}
                fallback={user?.fullName || user?.email || 'User'}
                size="md"
                showBorder
                className="h-9 w-9"
                type={userAvatar.avatarType}
              />
              {isOpen && (
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {user?.fullName || user?.email}
                  </p>
                  <p className="text-xs text-muted-foreground capitalize">
                    {user?.role}
                  </p>
                </div>
              )}
              {isOpen && (
                <div className="ml-auto">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleSignOut}
                    className="h-8 w-8 rounded-md border border-border text-muted-foreground hover:text-primary hover:border-primary/40"
                    title="Sign Out"
                    aria-label="Sign Out"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
          </div>
        </>
      )}
      </div>
    </div>
  );
};
