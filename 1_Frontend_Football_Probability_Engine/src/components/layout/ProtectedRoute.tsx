import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';
import { useContext } from 'react';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

// Create a safe wrapper that handles AuthContext not being available
function useAuthSafe() {
  try {
    return useAuth();
  } catch (error) {
    // If AuthProvider is not available, return default state
    return {
      isAuthenticated: false,
      isLoading: true,
      user: null,
      token: null,
      login: async () => {},
      loginDemo: async () => {},
      logout: async () => {},
      refreshAuth: async () => {},
    };
  }
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation();
  const { isAuthenticated, isLoading } = useAuthSafe();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
