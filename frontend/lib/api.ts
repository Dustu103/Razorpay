import type { ClassificationView, ListResponse } from '@/types/classification';

const AUDIT_URL = process.env.AUDIT_SERVICE_URL || 'http://localhost:3003';

export async function fetchClassifications(params: {
  cause?: string;
  layer?: string;
  limit?: number;
  offset?: number;
}): Promise<ListResponse> {
  const query = new URLSearchParams();
  if (params.cause) query.set('cause', params.cause);
  if (params.layer) query.set('layer', params.layer);
  query.set('limit', String(params.limit ?? 50));
  query.set('offset', String(params.offset ?? 0));

  const res = await fetch(`${AUDIT_URL}/api/v1/classifications?${query}`, {
    next: { revalidate: 5 }, // revalidate every 5s (fresh enough for demo)
  });
  if (!res.ok) throw new Error(`Audit service error: ${res.status}`);
  return res.json();
}

export async function fetchClassification(id: string): Promise<ClassificationView> {
  const res = await fetch(`${AUDIT_URL}/api/v1/classifications/${id}`, {
    next: { revalidate: 5 },
  });
  if (!res.ok) throw new Error(`Classification ${id} not found`);
  return res.json();
}

export function formatAmount(amount: number): string {
  return `₹${(amount / 100).toFixed(2)}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}
