// Shared TypeScript types for the Classifier Inspector frontend

export type Cause =
  | 'notification_compliance_block'
  | 'soft_decline'
  | 'hard_decline'
  | 'gateway_fault'
  | 'fraud_filter_block';

export type RecommendedAction =
  | 'silent_reschedule'
  | 'retry_now'
  | 'retry_scheduled'
  | 'do_not_retry'
  | 'reverify_and_reverse';

export interface ClassificationView {
  id: string;
  transaction_id: string;
  gateway_transaction_id: string;
  layer: 1 | 2;
  cause: Cause;
  confidence: number;
  reasoning: string;
  recommended_action: RecommendedAction;
  model_version: string | null;
  status_code: string;
  npci_response_code: string | null;
  bank_response_code: string | null;
  amount: number;
  customer_bank: string | null;
  retry_count_so_far: number;
  created_at: string;
}

export interface ListResponse {
  data: ClassificationView[];
  count: number;
}
