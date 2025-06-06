import React, { createContext, useContext, useEffect, useState } from 'react';
import { useClerk, useUser, useAuth } from '@clerk/clerk-react';

// Création du contexte d'authentification
const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const { isLoaded, isSignedIn, user } = useUser();
  const { getToken } = useAuth();
  const { signOut } = useClerk();
  const [authToken, setAuthToken] = useState(null);

  // Récupération initiale et stockage du token dans sessionStorage
  useEffect(() => {
    const fetchToken = async () => {
      if (isSignedIn) {
        try {
          const token = await getToken();
          setAuthToken(token);
          sessionStorage.setItem('authToken', token);
        } catch (error) {
          console.error('Error fetching token:', error);
          sessionStorage.removeItem('authToken');
        }
      } else {
        setAuthToken(null);
        sessionStorage.removeItem('authToken');
      }
    };

    if (isLoaded) {
      fetchToken();
    }
  }, [isLoaded, isSignedIn, getToken]);

  // Mécanisme de rafraîchissement du token (par exemple toutes les 15 secondes)
  useEffect(() => {
    let intervalId = null;

    const refreshToken = async () => {
      if (isSignedIn) {
        try {
          // Force le rafraîchissement du token
          const token = await getToken({ forceRefresh: true });
          setAuthToken(token);
          sessionStorage.setItem('authToken', token);
          console.log('Token rafraîchi');
        } catch (error) {
          console.error('Error refreshing token:', error);
        }
      }
    };

    // Définir l'intervalle pour rafraîchir le token régulièrement
    if (isSignedIn) {
      intervalId = setInterval(refreshToken, 15000); // toutes les 15 secondes, ajustez selon vos besoins
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isSignedIn, getToken]);

  // Fonction de déconnexion
  const handleSignOut = async () => {
    try {
      await signOut();
      sessionStorage.removeItem('authToken');
      return true;
    } catch (error) {
      console.error('Sign out error:', error);
      return false;
    }
  };

  // Fonction pour obtenir le rôle de l'utilisateur
  const getUserRole = () => {
    if (!isSignedIn || !user) return null;
    return user.publicMetadata?.role || 'user';
  };

  // Vérifie si l'utilisateur est administrateur
  const isUserAdmin = () => {
    return getUserRole() === 'admin';
  };

  // Fonction optionnelle pour récupérer le token à la demande
  const getAuthToken = async () => {
    if (!isSignedIn) return null;
    try {
      const token = await getToken({ forceRefresh: true });
      return token;
    } catch (error) {
      console.error('Error getting auth token:', error);
      return null;
    }
  };

  // Valeurs du contexte à fournir aux consommateurs
  const authValues = {
    isAuthenticated: isSignedIn,
    user: isSignedIn
      ? {
          id: user.id,
          firstName: user.firstName,
          lastName: user.lastName,
          email:
            user.emailAddresses && user.emailAddresses.length > 0
              ? user.emailAddresses[0].emailAddress
              : '',
          imageUrl: user.imageUrl,
        }
      : null,
    isAdmin: isUserAdmin(),
    userRole: getUserRole(),
    authLoading: !isLoaded,
    signOut: handleSignOut,
    authToken,       // Le token stocké dans le state et dans sessionStorage
    getAuthToken,    // Fonction pour récupérer à la demande un token mis à jour
  };

  return (
    <AuthContext.Provider value={authValues}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook personnalisé pour utiliser le contexte
export const useAppAuth = () => {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error('useAppAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
