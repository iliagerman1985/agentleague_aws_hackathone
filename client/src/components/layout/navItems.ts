import {
  LayoutDashboard,
  Users,
  BarChart3,
  Settings,
  HelpCircle,
} from 'lucide-react';

export interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
  iconColor?: string; // Tailwind color class for the icon
  children?: NavItem[]; // Support for nested navigation items
}

export const navItems: NavItem[] = [
  { title: 'Play', href: '/games-management', icon: LayoutDashboard, iconColor: 'text-blue-500' },
  { title: 'Agents', href: '/agents', icon: Users, iconColor: 'text-cyan-500' },
  { title: 'Leaderboard', href: '/leaderboard', icon: BarChart3, iconColor: 'text-yellow-500' },
  { title: 'Help', href: '/help', icon: HelpCircle, iconColor: 'text-pink-500' },
  { title: 'Settings', href: '/settings', icon: Settings, iconColor: 'text-gray-500' },
];
