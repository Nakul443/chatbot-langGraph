// This hook manages user authentication state, including login, registration, and logout functionality
// It interacts with the backend API to authenticate users and stores the authentication state in a global store
// The hook provides loading and error states to manage UI feedback during authentication processes

import { useAuthStore } from '@/store/authStore';
import { apiService } from '@/services/api';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export function useAuth() {
  const { user, token, setAuth, clearAuth } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  // This function handles both login and registration processes by interacting with the backend API
  // It updates the global authentication state upon successful authentication and navigates the user to the home page
  const handleAuth = async (email: string, password: string, mode: 'login' | 'signup') => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.auth(email, password, mode);
      setAuth(data.user, data.token);
      router.push('/');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await apiService.logout();
      clearAuth();
      router.push('/login');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Logout failed');
    } finally {
      setLoading(false);
    }
  };

  return {
    user,
    token,
    loading,
    error,
    login: (email: string, password: string) => handleAuth(email, password, 'login'),
    register: (email: string, password: string) => handleAuth(email, password, 'signup'),
    logout,
  };
}
