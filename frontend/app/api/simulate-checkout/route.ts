import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    
    // Try candidate URLs for ingestion service (Docker vs Localhost)
    const candidateUrls = [
      process.env.INGESTION_SERVICE_URL ? `${process.env.INGESTION_SERVICE_URL.replace(/\/$/, '')}/api/v1/checkout-events` : null,
      'http://ingestion-service:3001/api/v1/checkout-events',
      'http://localhost:3001/api/v1/checkout-events',
      'http://127.0.0.1:3001/api/v1/checkout-events',
    ].filter(Boolean) as string[];

    let response: Response | null = null;
    let lastError = '';

    for (const url of candidateUrls) {
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(3000),
        });
        if (res.ok) {
          response = res;
          break;
        } else {
          lastError = await res.text();
        }
      } catch (e: any) {
        lastError = e.message;
      }
    }

    if (!response) {
      return NextResponse.json({ error: 'Ingestion service unreachable', details: lastError }, { status: 502 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Error proxying checkout event:', error);
    return NextResponse.json({ error: 'Internal server error', message: error.message }, { status: 500 });
  }
}
