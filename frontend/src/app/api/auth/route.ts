// This file defines the API routes for user authentication, including login, signup, and logout
// It handles the communication with the backend authentication endpoints and manages auth tokens in cookies
// The POST method handles both login and signup based on the provided mode, while the DELETE method handles user logout

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email, password, mode } = body; // mode is 'login' or 'signup'

    const endpoint = mode === 'signup' ? '/auth/signup' : '/auth/login';
    const res = await fetch(`${BACKEND_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const errText = await res.text();
      return NextResponse.json({ error: errText || 'Authentication failed' }, { status: res.status });
    }

    const data = await res.json();
    const token = data.access_token || data.token;
    
    // Simple user extraction (or from response if backend returns it)
    const user = { id: email, email };

    const response = NextResponse.json({ user, token });

    if (token) {
      response.cookies.set('auth_token', token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
        maxAge: 60 * 60 * 24, // 24 hours
      });
    }

    return response;
  } catch (error: unknown) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Server error' }, { status: 500 });
  }
}

// this function handles user logout by clearing the auth token cookie
export async function DELETE() {
  const response = NextResponse.json({ success: true });
  response.cookies.set('auth_token', '', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  });
  return response;
}
