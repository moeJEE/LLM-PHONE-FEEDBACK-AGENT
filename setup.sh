#!/bin/bash
# Script to initialize the LLM Phone Feedback System project structure

# Create base directories
mkdir -p src/components/ui
mkdir -p src/components/auth
mkdir -p src/components/dashboard
mkdir -p src/components/knowledge
mkdir -p src/components/surveys
mkdir -p src/components/calls
mkdir -p src/components/layout
mkdir -p src/pages
mkdir -p src/context
mkdir -p src/services
mkdir -p src/utils

# Create placeholder files in each directory to maintain structure
# Components
touch src/components/ui/.gitkeep
touch src/components/auth/.gitkeep
touch src/components/dashboard/.gitkeep
touch src/components/knowledge/.gitkeep
touch src/components/surveys/.gitkeep
touch src/components/calls/.gitkeep
touch src/components/layout/.gitkeep

# Create basic layout components
cat > src/components/layout/Sidebar.jsx << 'EOL'
import React from 'react';

const Sidebar = () => {
  return (
    <div className="h-screen w-64 bg-gray-800 text-white p-4">
      <h2 className="text-xl font-bold mb-6">LLM Feedback System</h2>
      <nav>
        <ul className="space-y-2">
          <li><a href="/" className="block p-2 hover:bg-gray-700 rounded">Dashboard</a></li>
          <li><a href="/calls" className="block p-2 hover:bg-gray-700 rounded">Calls</a></li>
          <li><a href="/surveys" className="block p-2 hover:bg-gray-700 rounded">Surveys</a></li>
          <li><a href="/knowledge" className="block p-2 hover:bg-gray-700 rounded">Knowledge Base</a></li>
        </ul>
      </nav>
    </div>
  );
};

export default Sidebar;
EOL

cat > src/components/layout/Header.jsx << 'EOL'
import React from 'react';

const Header = () => {
  return (
    <header className="bg-white shadow p-4 flex justify-between items-center">
      <div>
        <h1 className="text-xl font-semibold text-gray-800">LLM Phone Feedback System</h1>
      </div>
      <div>
        <button className="bg-gray-800 text-white px-4 py-2 rounded">Sign Out</button>
      </div>
    </header>
  );
};

export default Header;
EOL

cat > src/components/layout/MainLayout.jsx << 'EOL'
import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

const MainLayout = ({ children }) => {
  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-x-hidden overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
EOL

# Create placeholder pages
cat > src/pages/Dashboard.jsx << 'EOL'
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
EOL

# Create context files
cat > src/context/AuthContext.js << 'EOL'
import React, { createContext, useState, useContext } from 'react';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

  const login = async (credentials) => {
    // Implement login logic
    setLoading(true);
    try {
      // Mock login
      setUser({ id: 1, name: 'Test User', email: 'test@example.com' });
      return true;
    } catch (error) {
      console.error(error);
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
EOL

# Create service file
cat > src/services/api.js << 'EOL'
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

export const fetchCalls = async () => {
  try {
    const response = await fetch(`${API_URL}/calls`);
    if (!response.ok) throw new Error('Failed to fetch calls');
    return await response.json();
  } catch (error) {
    console.error('Error fetching calls:', error);
    throw error;
  }
};

export const fetchSurveys = async () => {
  try {
    const response = await fetch(`${API_URL}/surveys`);
    if (!response.ok) throw new Error('Failed to fetch surveys');
    return await response.json();
  } catch (error) {
    console.error('Error fetching surveys:', error);
    throw error;
  }
};

export const fetchKnowledgeBase = async () => {
  try {
    const response = await fetch(`${API_URL}/knowledge`);
    if (!response.ok) throw new Error('Failed to fetch knowledge base');
    return await response.json();
  } catch (error) {
    console.error('Error fetching knowledge base:', error);
    throw error;
  }
};
EOL

# Create utils file
cat > src/utils/helpers.js << 'EOL'
export const formatDate = (dateString) => {
  const options = { year: 'numeric', month: 'long', day: 'numeric' };
  return new Date(dateString).toLocaleDateString(undefined, options);
};

export const truncateText = (text, maxLength = 100) => {
  if (text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
};

export const generateUniqueId = () => {
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
};
EOL

# Update App.js
cat > src/App.js << 'EOL'
import React from 'react';
import { AuthProvider } from './context/AuthContext';
import Dashboard from './pages/Dashboard';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  );
}

export default App;
EOL

# Update index.js to include Tailwind
cat > src/index.js << 'EOL'
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

reportWebVitals();
EOL

# Install shadcn components if needed
# npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-tabs

echo "Project structure created successfully!"