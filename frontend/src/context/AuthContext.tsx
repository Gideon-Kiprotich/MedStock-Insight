import React, { createContext, useContext, useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { User } from '../types/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  // JWT access token is stored in browser localStorage for the prototype.
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }, []);

  useEffect(() => {
    let active = true;
    const initAuth = async () => {
      if (token && !user) {
        try {
          const currentUser = await api.getCurrentUser();
          if (active) {
            setUser(currentUser);
            localStorage.setItem('user', JSON.stringify(currentUser));
          }
        } catch {
          if (active) logout();
        }
      }
      if (active) setIsLoading(false);
    };
    void initAuth();
    const handleAuthExpired = () => logout();
    window.addEventListener('auth-expired', handleAuthExpired);
    return () => { active = false; window.removeEventListener('auth-expired', handleAuthExpired); };
  }, [token, user, logout]);

  const login = async (email: string, pass: string) => {
    setIsLoading(true);
    try {
      const res = await api.login({ email, password: pass });
      localStorage.setItem('token', res.access_token);
      const currentUser = await api.getCurrentUser();
      setUser(currentUser);
      setToken(res.access_token);
      localStorage.setItem('user', JSON.stringify(currentUser));
    } catch (error) {
      logout();
      throw error;
    } finally {
      setIsLoading(false);
    }
  };



  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!token && !!user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
