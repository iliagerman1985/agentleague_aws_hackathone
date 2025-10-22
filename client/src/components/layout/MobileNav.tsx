import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronDown, ChevronUp } from 'lucide-react';

import { cn } from '@/lib/utils';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription
} from '@/components/ui/sheet';
import { Separator } from '@/components/ui/separator';
import { Logo } from '@/components/ui/logo';
import { useSidebar } from '@/contexts/SidebarContext';
import { useAuth } from '@/contexts/AuthContext';
import { useAvatar } from '@/contexts/AvatarContext';
import { Avatar } from '@/components/common/Avatar';

import { navItems, NavItem } from './navItems';

export const MobileNav: React.FC = () => {
  const { isOpen, close } = useSidebar();
  const { user, signOut } = useAuth();
  const { userAvatar } = useAvatar();
  const location = useLocation();
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (e) {
      console.error('Sign out error:', e);
    }
  };

  const toggleExpanded = (title: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev);
      if (next.has(title)) {
        next.delete(title);
      } else {
        next.add(title);
      }
      return next;
    });
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
    <Sheet open={isOpen} onOpenChange={(open) => !open && close()}>
      <SheetContent side="left" className="w-64 p-0 flex flex-col bg-secondary sidebar-surface text-foreground border-2 border-primary shadow-lg shadow-black/20">
        <SheetHeader className="p-6 border-b border-border/30 sidebar-logo-bg">
          <SheetTitle className="flex w-full items-center justify-center">
            <Link to="/games-management" onClick={close} className="hover:opacity-80 transition-opacity">
              <Logo width={400} height={112} color="none" className="h-28 w-auto" />
            </Link>
          </SheetTitle>
          <SheetDescription className="sr-only">Navigation menu</SheetDescription>
        </SheetHeader>

        <nav className="flex-1 space-y-1.5 p-3 bg-transparent">
          {filteredNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = isItemActive(item);
            const isExpanded = expandedItems.has(item.title);
            const hasChildren = item.children && item.children.length > 0;

            return (
              <div key={item.href}>
                {/* Parent Item */}
                {hasChildren ? (
                  <div className="flex items-center gap-1">
                    <Link
                      to={item.href}
                      onClick={close}
                      className={cn(
                        "sidebar-link group flex items-center gap-3.5 rounded-lg px-3.5 py-2.5 font-medium text-base transition-all duration-200 ring-1 ring-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 flex-1",
                        isActive ? "is-active" : ""
                      )}
                    >
                      <Icon className={cn("h-5 w-5 flex-shrink-0 transition-colors", isActive ? "text-white" : item.iconColor || "text-muted-foreground", !isActive && "group-hover:text-primary")} />
                      <span className="leading-snug flex-1 text-left">{item.title}</span>
                    </Link>
                    <button
                      onClick={() => toggleExpanded(item.title)}
                      className="p-2 hover:bg-accent rounded-md transition-colors"
                      aria-label={isExpanded ? "Collapse" : "Expand"}
                    >
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                ) : (
                  <Link
                    to={item.href}
                    onClick={close}
                    className={cn(
                      "sidebar-link group flex items-center gap-3.5 rounded-lg px-3.5 py-2.5 font-medium text-base transition-all duration-200 ring-1 ring-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
                      isActive ? "is-active" : ""
                    )}
                  >
                    <Icon className={cn("h-5 w-5 flex-shrink-0 transition-colors", isActive ? "text-white" : item.iconColor || "text-muted-foreground", !isActive && "group-hover:text-primary")} />
                    <span className="leading-snug">{item.title}</span>
                  </Link>
                )}

                {/* Child Items */}
                {hasChildren && isExpanded && (
                  <div className="ml-8 mt-1 space-y-1">
                    {item.children!.map((child) => {
                      const ChildIcon = child.icon;
                      const isChildActive = location.pathname === child.href;

                      return (
                        <Link
                          key={child.href}
                          to={child.href}
                          onClick={close}
                          className={cn(
                            "sidebar-link group flex items-center gap-3 rounded-lg px-3 py-2 font-medium text-sm transition-all duration-200 ring-1 ring-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
                            isChildActive ? "is-active" : ""
                          )}
                        >
                          <ChildIcon
                            className={cn(
                              "h-4 w-4 flex-shrink-0 transition-colors",
                              isChildActive ? "text-primary" : child.iconColor || "text-muted-foreground",
                              "group-hover:text-primary"
                            )}
                          />
                          <span className="leading-snug">{child.title}</span>
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        <div className="mt-auto">
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
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {user?.fullName || user?.email}
                </p>
                <p className="text-xs text-muted-foreground capitalize">
                  {user?.role}
                </p>
              </div>
              <button onClick={handleSignOut} className="h-8 w-8 inline-flex items-center justify-center rounded-md border border-border text-muted-foreground hover:text-primary hover:border-primary/40" aria-label="Sign Out" title="Sign Out">
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>
              </button>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};
