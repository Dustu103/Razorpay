'use server';

import { revalidatePath } from 'next/cache';

const INGESTION_URL = process.env.INGESTION_SERVICE_URL || 'http://localhost:3001';

export async function simulateWebhook(payload: Record<string, any>) {
  try {
    const res = await fetch(`${INGESTION_URL}/api/v1/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text();
      return { success: false, error: `Backend responded with ${res.status}: ${text}` };
    }

    // Give the backend a brief moment to process the queue so it appears on the frontend
    await new Promise(r => setTimeout(r, 1500));
    
    revalidatePath('/'); // Trigger UI refresh

    return { success: true };
  } catch (error: any) {
    return { success: false, error: error.message || 'Unknown error occurred' };
  }
}
