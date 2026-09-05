import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    
    // Send to ingestion-service via internal docker network
    const ingestionUrl = 'http://ingestion-service:3001/api/v1/checkout-events';
    
    const response = await fetch(ingestionUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json({ error: 'Ingestion service failed', details: errorText }, { status: response.status });
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Error proxying checkout event:', error);
    return NextResponse.json({ error: 'Internal server error', message: error.message }, { status: 500 });
  }
}
