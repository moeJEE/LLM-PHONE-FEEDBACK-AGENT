import React, { createContext, useContext, useEffect, useState } from 'react';
import { useClerk, useUser, useAuth } from '@clerk/clerk-react';

// Création du contexte d'authentification
const AuthContext = createContext({});

export const AuthProvider = ({ children }) => {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { user } = useUser();
  const { signOut } = useClerk();
  const [userToken, setUserToken] = useState(null);
  const [lastTokenFetch, setLastTokenFetch] = useState(null);
  const [tokenError, setTokenError] = useState(null);

  const fetchUserToken = async () => {
    try {
      if (!isSignedIn) {
        setUserToken(null);
        setTokenError(null);
        return null;
      }
      const token = await getToken();
      setUserToken(token);
      setLastTokenFetch(Date.now());
      setTokenError(null);
      return token;
    } catch (error) {
      setTokenError('Failed to fetch authentication token');
      return null;
    }
  };

  const refreshToken = async () => {
    try {
      if (!isSignedIn) {
        setUserToken(null);
        return null;
      }
      const token = await getToken({ template: 'default' });
      setUserToken(token);
      setLastTokenFetch(Date.now());
      setTokenError(null);
      return token;
    } catch (error) {
      setTokenError('Failed to refresh authentication token');
      return null;
    }
  };

  const handleSignOut = async () => {
    try {
      setUserToken(null);
      setLastTokenFetch(null);
      setTokenError(null);
      await signOut();
      return true;
    } catch (error) {
      setTokenError('Failed to sign out');
      return false;
    }
  };

  const getUserInfo = () => {
    if (!user) {
      return null;
    }
    return {
      id: user.id,
      email: user.primaryEmailAddress?.emailAddress,
      firstName: user.firstName,
      lastName: user.lastName,
      imageUrl: user.imageUrl,
    };
  };

  const getUserRole = () => {
    if (!isSignedIn || !user) return null;
    return user.publicMetadata?.role || 'user';
  };

  const isUserAdmin = () => {
    return getUserRole() === 'admin';
  };

  const getAuthToken = async () => {
    try {
      // If we have a recent token (less than 5 minutes old), use it
      if (userToken && lastTokenFetch && (Date.now() - lastTokenFetch) < 300000) {
        return userToken;
      }
      
      // Otherwise, fetch a new token
      return await fetchUserToken();
    } catch (error) {
      setTokenError('Failed to get authentication token');
      return null;
    }
  };

  // Auto-refresh token on auth state changes
  useEffect(() => {
    if (isLoaded && isSignedIn) {
      fetchUserToken();
    } else if (isLoaded && !isSignedIn) {
      setUserToken(null);
      setLastTokenFetch(null);
      setTokenError(null);
    }
  }, [isLoaded, isSignedIn]);

  const value = {
    isLoaded,
    isSignedIn,
    user: getUserInfo(),
    userToken,
    tokenError,
    fetchUserToken,
    refreshToken,
    signOut: handleSignOut,
    getAuthToken,
    getUserRole,
    isUserAdmin,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook pour utiliser le contexte d'authentification
export const useAppAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAppAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
