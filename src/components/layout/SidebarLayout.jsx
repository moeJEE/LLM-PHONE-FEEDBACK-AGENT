import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, PhoneCall, FileText, MessageSquare, BarChart, Settings, Users, LogOut, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { useClerk, useUser } from '@clerk/clerk-react';

const SidebarLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { signOut } = useClerk();
  const { user, isLoaded } = useUser();
  
  const [collapsed, setCollapsed] = useState(false);

  const getUserInitials = () => {
    if (!isLoaded || !user) return '?';
    const firstName = user.firstName || '';
    const lastName = user.lastName || '';
    return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
  };

  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
  };

  const toggleSidebar = () => {
    setCollapsed(!collapsed);
  };

  const navigationItems = [
    { icon: <LayoutDashboard size={20} />, label: 'Dashboard', href: '/dashboard' },
    { icon: <PhoneCall size={20} />, label: 'Call Management', href: '/calls' },
    { icon: <FileText size={20} />, label: 'Knowledge Base', href: '/knowledge' },
    { icon: <MessageSquare size={20} />, label: 'Survey Builder', href: '/surveys' },
    { icon: <BarChart size={20} />, label: 'Analytics', href: '/analytics' },
    { icon: <Zap size={20} />, label: 'Optimization', href: '/optimization' },
    { icon: <Users size={20} />, label: 'User Management', href: '/users' },
    { icon: <Settings size={20} />, label: 'Settings', href: '/settings' },
  ];

  const NavItem = ({ item }) => (
    <a 
      href={item.href}
      className={`flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors ${
        location.pathname === item.href
          ? 'bg-blue-100 text-blue-700'
          : 'text-gray-700 hover:bg-gray-100'
      }`}
      onClick={(e) => {
        e.preventDefault();
        navigate(item.href);
      }}
    >
      <span className="mr-3">{item.icon}</span>
      {!collapsed && <span>{item.label}</span>}
    </a>
  );

  return (
    <aside className={`flex flex-col bg-white border-r border-gray-200 transition-all duration-300 ease-in-out ${collapsed ? 'w-20' : 'w-64'}`}>
      <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
        <div className="flex items-center">
          <div className="h-8 w-8 bg-blue-600 rounded-md flex items-center justify-center text-white font-bold">
            AP
          </div>
          {!collapsed && <span className="ml-3 font-semibold text-gray-900">Mon Application</span>}
        </div>
        <Button variant="ghost" size="icon" onClick={toggleSidebar}>
          {collapsed ? <LayoutDashboard size={20} /> : <Settings size={20} />}
        </Button>
      </div>
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {navigationItems.map((item, index) => (
          <NavItem key={index} item={item} />
        ))}
      </nav>
      {/* User info at bottom */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex items-center space-x-3">
          <Avatar>
            <AvatarImage src={user?.imageUrl} alt="User avatar" />
            <AvatarFallback>{getUserInitials()}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              {user?.firstName} {user?.lastName}
            </p>
            <p className="truncate text-xs text-gray-500">
              {user?.emailAddresses?.[0]?.emailAddress}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleSignOut}
            title="Sign out"
          >
            <LogOut size={16} />
          </Button>
        </div>
      </div>
    </aside>
  );
};

export default SidebarLayout;