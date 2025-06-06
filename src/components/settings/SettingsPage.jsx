import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Settings as SettingsIcon, 
  Phone, 
  User, 
  Shield, 
  Bell, 
  Palette, 
  Globe, 
  Database, 
  Key,
  Save,
  Trash2
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';

const SettingsPage = () => {
  const navigate = useNavigate();
  
  // Define the settings categories
  const settingsCategories = [
    { 
      id: 'integrations', 
      label: 'Integrations', 
      icon: <Database className="h-5 w-5 mr-2" />,
      description: 'Configure external service integrations',
      items: [
        { id: 'twilio', label: 'Twilio Integration', icon: <Phone />, path: '/settings/twilio' },
        { id: 'llm', label: 'LLM Provider', icon: <Key />, path: '/settings/llm' }
      ]
    },
    { 
      id: 'users', 
      label: 'User & Permissions', 
      icon: <Shield className="h-5 w-5 mr-2" />,
      description: 'Manage user access and permissions',
      items: [
        { id: 'roles', label: 'Role Management', icon: <User />, path: '/settings/roles' },
        { id: 'permissions', label: 'Permissions', icon: <Shield />, path: '/settings/permissions' }
      ]
    },
    { 
      id: 'notifications', 
      label: 'Notifications', 
      icon: <Bell className="h-5 w-5 mr-2" />,
      description: 'Configure system notifications and alerts',
      items: [
        { id: 'email', label: 'Email Notifications', icon: <Bell />, path: '/settings/email-notifications' },
        { id: 'app', label: 'In-App Notifications', icon: <Bell />, path: '/settings/app-notifications' }
      ]
    },
    { 
      id: 'appearance', 
      label: 'Appearance', 
      icon: <Palette className="h-5 w-5 mr-2" />,
      description: 'Customize the look and feel of the application',
      items: [
        { id: 'theme', label: 'Theme Settings', icon: <Palette />, path: '/settings/theme' }
      ]
    },
    { 
      id: 'general', 
      label: 'General', 
      icon: <SettingsIcon className="h-5 w-5 mr-2" />,
      description: 'General system settings',
      items: [
        { id: 'language', label: 'Language & Region', icon: <Globe />, path: '/settings/language' },
        { id: 'data', label: 'Data Management', icon: <Database />, path: '/settings/data' }
      ]
    }
  ];

  const handleNavigate = (path) => {
    navigate(path);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-gray-500">Configure your system preferences and integrations</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Settings Categories */}
        {settingsCategories.map((category) => (
          <Card key={category.id} className="overflow-hidden">
            <CardHeader className="bg-muted/50">
              <CardTitle className="flex items-center">
                {category.icon}
                {category.label}
              </CardTitle>
              <CardDescription>{category.description}</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <ul className="divide-y">
                {category.items.map((item) => (
                  <li key={item.id}>
                    <Button
                      variant="ghost"
                      className="w-full justify-start rounded-none h-auto py-3 px-4"
                      onClick={() => handleNavigate(item.path)}
                    >
                      <div className="flex items-center">
                        <div className="mr-3 text-gray-500">
                          {item.icon}
                        </div>
                        <div>{item.label}</div>
                      </div>
                    </Button>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default SettingsPage;