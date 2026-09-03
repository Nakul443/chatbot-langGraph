// This middleware checks for user authentication based on the presence of an auth token in cookies
// It redirects unauthenticated users to the login page and prevents authenticated users from accessing the login or register pages

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token')?.value;
  const isAuthPage = request.nextUrl.pathname.startsWith('/login') || request.nextUrl.pathname.startsWith('/register');

  // If no token and not on /login or /register, redirect to /login
  if (!token && !isAuthPage) {
    const loginUrl = new URL('/login', request.url);
    return NextResponse.redirect(loginUrl);
  }

  // If token exists and user goes to /login or /register, redirect to root
  if (token && isAuthPage) {
    const rootUrl = new URL('/', request.url);
    return NextResponse.redirect(rootUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Check all paths except static assets, favicon, api/auth routes
  matcher: [
    '/((?!api/auth|_next/static|_next/image|favicon.ico).*)',
  ],
};
