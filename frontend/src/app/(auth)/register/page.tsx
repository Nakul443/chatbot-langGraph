// This file defines the RegisterPage component, which provides a user interface for registering a new account in the LangGraph Chatbot application.
// It includes form fields for email, password, and password confirmation, along with validation logic to ensure proper input. The component interacts with the authentication service to create a new user account and handles loading and error states during the registration process.

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { Button, Input } from '@/components/ui';
import { MessageSquareCode } from 'lucide-react';

export default function RegisterPage() {
  const { register, loading, error: authError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!email || !password || !confirmPassword) return;

    if (password !== confirmPassword) {
      setValidationError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setValidationError('Password must be at least 6 characters long');
      return;
    }

    await register(email, password);
  };

  const displayError = validationError || authError;

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8 bg-zinc-900 border border-zinc-850 p-8 rounded-2xl shadow-2xl">
        <div className="text-center space-y-3">
          <div className="inline-flex p-3 rounded-2xl bg-blue-600/10 text-blue-400 border border-blue-500/15">
            <MessageSquareCode className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-zinc-100">Create your account</h2>
          <p className="text-sm text-zinc-400">Get started with LangGraph Chatbot</p>
        </div>

        {displayError && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400 leading-relaxed">
            {displayError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <Input
            type="email"
            label="Email Address"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            required
          />

          <Input
            type="password"
            label="Password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            required
          />

          <Input
            type="password"
            label="Confirm Password"
            placeholder="••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={loading}
            required
          />

          <Button type="submit" className="w-full py-3" loading={loading}>
            Create Account
          </Button>
        </form>

        <p className="text-center text-sm text-zinc-500">
          Already have an account?{' '}
          <Link href="/login" className="text-blue-400 hover:underline font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
