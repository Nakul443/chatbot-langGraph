// This file defines the apiService object that provides
// methods for interacting with the backend API for authentication and chat functionalities.
// It includes methods for user login, signup, logout, fetching chat threads, retrieving message history, and uploading files.

// basically connects all the frontend api calls to the backend api endpoints

export const apiService = {
  async auth(email: string, password: string, mode: 'login' | 'signup') {
    const res = await fetch('/api/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, mode }),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || 'Authentication failed');
    }
    return res.json();
  },

  async logout() {
    const res = await fetch('/api/auth', { method: 'DELETE' });
    if (!res.ok) {
      throw new Error('Logout failed');
    }
  },

  async getThreads() {
    const res = await fetch('/api/chat');
    if (!res.ok) {
      throw new Error('Failed to fetch threads');
    }
    return res.json();
  },

  async getHistory(threadId: string) {
    const res = await fetch(`/api/chat?threadId=${encodeURIComponent(threadId)}`);
    if (!res.ok) {
      throw new Error('Failed to fetch message history');
    }
    return res.json();
  },

  async uploadFile(file: File, threadId: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('thread_id', threadId);

    const res = await fetch('/api/chat', {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({ error: 'File upload failed' }));
      throw new Error(data.error || 'File upload failed');
    }

    // Read the stream to completion to ensure the upload and ingestion are fully processed
    const reader = res.body?.getReader();
    if (reader) {
      while (true) {
        const { done } = await reader.read();
        if (done) break;
      }
    }

    return res;
  }
};
