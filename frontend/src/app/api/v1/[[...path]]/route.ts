import { NextRequest, NextResponse } from 'next/server';

// Runtime API URL - not baked in at build time
const API_URL = process.env.API_URL || 'http://localhost:8000';

async function proxyRequest(request: NextRequest, path: string[]): Promise<NextResponse> {
  const url = new URL(request.url);
  const targetPath = path ? path.join('/') : '';
  const targetUrl = `${API_URL}/api/v1/${targetPath}${url.search}`;

  const headers = new Headers();
  
  // Forward relevant headers
  const authHeader = request.headers.get('authorization');
  if (authHeader) {
    headers.set('Authorization', authHeader);
  }
  
  const contentType = request.headers.get('content-type');
  if (contentType) {
    headers.set('Content-Type', contentType);
  }

  try {
    const body = request.method !== 'GET' && request.method !== 'HEAD' 
      ? await request.text() 
      : undefined;

    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body,
    });

    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      // Don't forward certain headers
      if (!['content-encoding', 'transfer-encoding', 'connection'].includes(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });

    const data = await response.text();
    
    return new NextResponse(data, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to proxy request to API' },
      { status: 502 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

