import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ClerkProvider, SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react';
import { AuthProvider } from './context/AuthContext';
import AuthPage from './components/auth/AuthPage';
import Dashboard from './components/dashboard/Dashboard';
import MainLayout from './components/layout/MainLayout';
import './App.css';

import CallManagement from './components/calls/CallManagement';
import KnowledgeManagement from './components/knowledge/KnowledgeManagement';
import SurveyBuilder from './components/surveys/SurveyBuilder';
import SettingsPage from './components/settings/SettingsPage';
import UserManagement from './components/users/UserManagement';
import TwilioIntegration from './components/settings/TwilioIntegration';
import OptimizationDashboard from './components/optimization/OptimizationDashboard';

const clerkPubKey = process.env.REACT_APP_CLERK_PUBLISHABLE_KEY;

const ProtectedRoute = ({ children }) => (
  <>
    <SignedIn>{children}</SignedIn>
    <SignedOut>
      <RedirectToSignIn />
    </SignedOut>
  </>
);

function App() {
  if (!clerkPubKey) {
    return <div>Missing Clerk Publishable Key</div>;
  }

  return (
    <ClerkProvider publishableKey={clerkPubKey}>
      <AuthProvider>
        <Router>
          <Routes>
            {/* Routes publiques */}
            <Route
              path="/"
              element={
                <>
                  <SignedIn>
                    <Navigate to="/dashboard" replace />
                  </SignedIn>
                  <SignedOut>
                    <Navigate to="/login" replace />
                  </SignedOut>
                </>
              }
            />
            <Route path="/login" element={<AuthPage />} />
            <Route path="/sign-in" element={<Navigate to="/login" replace />} />

            {/* Routes protégées encapsulées dans MainLayout */}
            <Route
              element={
                <ProtectedRoute>
                  <MainLayout />
                </ProtectedRoute>
              }
            >
              {/* Redirection par défaut vers /dashboard */}
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="calls" element={<CallManagement />} />
              <Route path="knowledge" element={<KnowledgeManagement />} />
              <Route path="surveys" element={<SurveyBuilder />} />
              
              {/* Routes pour les paramètres et sous-routes */}
              <Route path="settings" element={<SettingsPage />} />
              <Route path="settings/twilio" element={<TwilioIntegration />} />
              
              {/* Routes pour la gestion des utilisateurs */}
              <Route path="users" element={<UserManagement />} />
              <Route path="user" element={<UserManagement />} />
              
              {/* Route pour l'optimisation */}
              <Route path="optimization" element={<OptimizationDashboard />} />
            </Route>

            {/* Route de fallback pour toute URL non reconnue */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ClerkProvider>
  );
}

export default App;