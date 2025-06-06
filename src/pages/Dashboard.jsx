import React from 'react';
import MainLayout from '../components/layout/MainLayout';

const Dashboard = () => {
  return (
    <MainLayout>
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-blue-100 p-4 rounded-lg">
            <h3 className="font-semibold text-lg">Recent Calls</h3>
            <p className="text-3xl font-bold">24</p>
          </div>
          <div className="bg-green-100 p-4 rounded-lg">
            <h3 className="font-semibold text-lg">Active Surveys</h3>
            <p className="text-3xl font-bold">3</p>
          </div>
          <div className="bg-purple-100 p-4 rounded-lg">
            <h3 className="font-semibold text-lg">Knowledge Base</h3>
            <p className="text-3xl font-bold">42</p>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default Dashboard;
