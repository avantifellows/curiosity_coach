import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '../types';
import { verifyAuthStatus } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Check if user is stored in localStorage AND verify it
    const checkAuth = async () => {
      setIsLoading(true);
      const storedUserTokenInfo = localStorage.getItem('user'); // Assume this stores necessary info (like ID for the bearer token)

      if (storedUserTokenInfo) {
        try {
          // Attempt to verify the session with the backend
          // verifyAuthStatus uses the interceptor which reads localStorage itself
          const verifiedUser = await verifyAuthStatus(); 
          
          // If verification is successful, set the user state
          setUser(verifiedUser);
          setIsAuthenticated(true);
          console.log("Session verified successfully.");

        } catch (error) {
          // If verification fails (401 etc.), clear storage and state
          console.error("Session verification failed:", error);
          localStorage.removeItem('user');
          setUser(null);
          setIsAuthenticated(false);
        }
      } else {
        // No stored info, definitely not logged in
        setUser(null);
        setIsAuthenticated(false);
      }
      
      // Loading finished whether verified, failed, or no token found
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = (user: User) => {
    localStorage.setItem('user', JSON.stringify(user));
    setUser(user);
    setIsAuthenticated(true);
  };

  const logout = () => {
    localStorage.removeItem('user');
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}; 