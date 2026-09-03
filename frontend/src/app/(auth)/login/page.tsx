// This file defines the LoginPage component, which provides a user interface for logging into the LangGraph Chatbot application.

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { Button, Input } from '@/components/ui';
import { KeyRound, Mail, MessageSquareCode } from 'lucide-react';

export default function LoginPage() {
  const { login, loading, error } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    await login(email, password);
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8 bg-zinc-900 border border-zinc-850 p-8 rounded-2xl shadow-2xl">
        <div className="text-center space-y-3">
          <div className="inline-flex p-3 rounded-2xl bg-blue-600/10 text-blue-400 border border-blue-500/15">
            <MessageSquareCode className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-zinc-100">Welcome back</h2>
          <p className="text-sm text-zinc-400">Sign in to your LangGraph Chatbot account</p>
        </div>

        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400 leading-relaxed">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="relative">
            <Input
              type="email"
              label="Email Address"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <div className="relative">
            <Input
              type="password"
              label="Password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <Button type="submit" className="w-full py-3" loading={loading}>
            Sign In
          </Button>
        </form>

        <p className="text-center text-sm text-zinc-500">
          Don&apos;t have an account?{' '}
          <Link href="/register" className="text-blue-400 hover:underline font-medium">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
