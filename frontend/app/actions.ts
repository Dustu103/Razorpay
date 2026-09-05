'use server';

import { revalidatePath } from 'next/cache';

export async function simulateWebhook(payload: Record<string, any>) {
  try {
    // Deep copy and generate a unique transaction ID so it never gets dropped as duplicate
    const cloned = JSON.parse(JSON.stringify(payload));
    const entity = cloned?.payload?.payment?.entity;
    if (entity) {
      const base = entity.id || 'pay_test';
      entity.id = `${base}_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
      // Ensure status_code is set if only status was provided
      if (!entity.status_code && entity.status) {
        entity.status_code = entity.status === 'failed' ? 'BAD_REQUEST_ERROR' : entity.status.toUpperCase();
      }
    }

    const candidateUrls = [
      process.env.INGESTION_SERVICE_URL,
      'http://ingestion-service:3001',
      'http://localhost:3001',
      'http://127.0.0.1:3001',
    ].filter(Boolean) as string[];

    let lastError = '';
    let success = false;
    let responseData: any = null;

    for (const baseUrl of candidateUrls) {
      try {
        const url = `${baseUrl.replace(/\/$/, '')}/api/v1/webhook`;
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(cloned),
          signal: AbortSignal.timeout(4000),
        });

        if (res.ok) {
          responseData = await res.json();
          success = true;
          break;
        } else {
          const text = await res.text();
          lastError = `Backend returned ${res.status}: ${text}`;
        }
      } catch (err: any) {
        lastError = err.message || 'Connection failed';
      }
    }

    if (!success) {
      return { success: false, error: `Ingestion service unreachable: ${lastError}` };
    }

    // Give backend worker time to consume from Redis queue and save to Postgres
    await new Promise(r => setTimeout(r, 1200));
    revalidatePath('/');

    return { 
      success: true, 
      transactionId: entity?.id || responseData?.transaction_id,
      status: responseData?.status 
    };
  } catch (error: any) {
    return { success: false, error: error.message || 'Unknown error occurred' };
  }
}
