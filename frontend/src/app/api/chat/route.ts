// This file defines the API routes for chat interactions, including fetching threads, streaming messages, and handling file uploads
// It manages the communication with the backend chat endpoints and
// ensures that requests are authenticated using the auth token from cookies
// The GET method fetches chat threads or message history,
// while the POST method handles streaming messages or file uploads based on the request content type

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const token = request.cookies.get('auth_token')?.value;

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const threadId = searchParams.get('threadId');

    let endpoint = '/chat/threads';
    if (threadId) {
      endpoint = `/chat/history/${threadId}`;
    }

    const res = await fetch(`${BACKEND_URL}${endpoint}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      const errText = await res.text();
      return NextResponse.json({ error: errText || 'Failed to fetch' }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: unknown) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Server error' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const token = request.cookies.get('auth_token')?.value;

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Proxy the stream or file upload
    // proxy means that the frontend will forward the request to the backend and return the response back to the client
    const contentType = request.headers.get('content-type') || '';
    
    if (contentType.includes('multipart/form-data')) {
      // File upload proxy
      const incomingFormData = await request.formData();
      const formData = new FormData();
      
      for (const [key, value] of incomingFormData.entries()) {
        if (value instanceof Blob) {
          const filename = (value as File).name || 'file.pdf';
          formData.append(key, value, filename);
        } else {
          formData.append(key, value);
        }
      }

      const res = await fetch(`${BACKEND_URL}/chat/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text();
        return NextResponse.json({ error: errText || 'Upload failed' }, { status: res.status });
      }

      // Handle stream proxying
      return new NextResponse(res.body, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    } else {
      // JSON streaming or regular call
      const body = await request.json();
      const res = await fetch(`${BACKEND_URL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        return NextResponse.json({ error: 'Stream initiation failed' }, { status: res.status });
      }

      // Handle stream proxying
      return new NextResponse(res.body, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    }
  } catch (error: unknown) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Server error' }, { status: 500 });
  }
}
