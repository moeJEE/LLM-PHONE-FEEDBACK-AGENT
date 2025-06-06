import React from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import SidebarLayout from './SidebarLayout';

const MainLayout = () => {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <SidebarLayout />

      {/* Zone de contenu principale */}
      <div className="flex flex-col flex-1">
        {/* Header */}
        <Header />

        {/* Contenu dynamique (pages enfants) */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
