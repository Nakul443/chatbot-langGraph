// This hook fetches and manages the state of chat threads for the user
// It provides loading and error states, and a refetch function to reload threads on demand
// It ensures that the UI can display the latest threads and handle any errors during the fetch process

import { useState, useEffect, useCallback } from 'react';
import { apiService } from '@/services/api';
import { Thread } from '@/types/chat';

export function useThreads() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(true); // Default to true as we fetch on mount
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  const refetch = useCallback(() => {
    setLoading(true);
    setError(null);
    setTrigger((prev) => prev + 1);
  }, []);

  useEffect(() => {
    let active = true;

    apiService.getThreads()
      .then((data) => {
        if (active) {
          setThreads(Array.isArray(data) ? data : []);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to fetch threads');
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [trigger]);

  return {
    threads,
    loading,
    error,
    refetch,
  };
}