import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface SidebarContextType {
  isOpen: boolean;
  isMobile: boolean;
  toggle: () => void;
  open: () => void;
  close: () => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export const useSidebar = () => {
  const context = useContext(SidebarContext);
  if (context === undefined) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
};

interface SidebarProviderProps {
  children: ReactNode;
}

export const SidebarProvider: React.FC<SidebarProviderProps> = ({ children }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  // Check if we're on mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Load sidebar state from localStorage on desktop
  useEffect(() => {
    if (!isMobile) {
      const savedState = localStorage.getItem('sidebar-open');
      if (savedState !== null) {
        setIsOpen(JSON.parse(savedState));
      } else {
        setIsOpen(true); // Default to open on desktop
      }
    } else {
      setIsOpen(false); // Always closed on mobile initially
    }
    setIsInitialized(true);
  }, [isMobile]);

  // Save sidebar state to localStorage (only for desktop)
  useEffect(() => {
    if (!isMobile && isInitialized) {
      localStorage.setItem('sidebar-open', JSON.stringify(isOpen));
    }
  }, [isOpen, isMobile, isInitialized]);

  const toggle = () => setIsOpen(prev => !prev);
  const open = () => setIsOpen(true);
  const close = () => setIsOpen(false);

  const value: SidebarContextType = {
    isOpen,
    isMobile,
    toggle,
    open,
    close,
  };

  return (
    <SidebarContext.Provider value={value}>
      {children}
    </SidebarContext.Provider>
  );
};
