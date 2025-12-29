import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import type { AuthState, User, LoginCredentials } from '@/types';
import { apiClient } from '@/services/api';

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  loginDemo: () => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

type AuthAction =
  | { type: 'AUTH_START' }
  | { type: 'AUTH_SUCCESS'; payload: { user: User; token: string } }
  | { type: 'AUTH_FAILURE' }
  | { type: 'LOGOUT' };

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'AUTH_START':
      return { ...state, isLoading: true };
    case 'AUTH_SUCCESS':
      return {
        user: action.payload.user,
        token: action.payload.token,
        isAuthenticated: true,
        isLoading: false,
      };
    case 'AUTH_FAILURE':
    case 'LOGOUT':
      return {
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      };
    default:
      return state;
  }
}

const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,
};

const DEMO_USER: User = {
  id: 'demo-user',
  email: 'demo@example.com',
  name: 'Demo Analyst',
};

const DEMO_TOKEN = 'demo-token-12345';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  const login = useCallback(async (credentials: LoginCredentials) => {
    dispatch({ type: 'AUTH_START' });
    try {
      const response = await apiClient.login(credentials);
      localStorage.setItem('auth_token', response.token);
      localStorage.removeItem('demo_mode');
      apiClient.setToken(response.token);
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: { user: response.user, token: response.token },
      });
    } catch (error) {
      dispatch({ type: 'AUTH_FAILURE' });
      throw error;
    }
  }, []);

  const loginDemo = useCallback(async () => {
    dispatch({ type: 'AUTH_START' });
    // Simulate a brief delay for UX
    await new Promise(resolve => setTimeout(resolve, 500));
    localStorage.setItem('auth_token', DEMO_TOKEN);
    localStorage.setItem('demo_mode', 'true');
    dispatch({
      type: 'AUTH_SUCCESS',
      payload: { user: DEMO_USER, token: DEMO_TOKEN },
    });
  }, []);

  const logout = useCallback(async () => {
    const isDemoMode = localStorage.getItem('demo_mode') === 'true';
    
    if (!isDemoMode) {
      try {
        await apiClient.logout();
      } catch (error) {
        console.error('Logout error:', error);
      }
    }
    
    localStorage.removeItem('auth_token');
    localStorage.removeItem('demo_mode');
    apiClient.setToken(null);
    dispatch({ type: 'LOGOUT' });
  }, []);

  const refreshAuth = useCallback(async () => {
    const storedToken = localStorage.getItem('auth_token');
    const isDemoMode = localStorage.getItem('demo_mode') === 'true';
    
    if (!storedToken) {
      dispatch({ type: 'AUTH_FAILURE' });
      return;
    }

    // Demo mode - restore session immediately
    if (isDemoMode && storedToken === DEMO_TOKEN) {
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: { user: DEMO_USER, token: DEMO_TOKEN },
      });
      return;
    }

    // Real auth - verify with backend
    dispatch({ type: 'AUTH_START' });
    try {
      apiClient.setToken(storedToken);
      const response = await apiClient.getCurrentUser();
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: { user: response.data.user, token: storedToken },
      });
    } catch (error) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('demo_mode');
      apiClient.setToken(null);
      dispatch({ type: 'AUTH_FAILURE' });
    }
  }, []);

  useEffect(() => {
    refreshAuth();
  }, [refreshAuth]);

  return (
    <AuthContext.Provider value={{ ...state, login, loginDemo, logout, refreshAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
