from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class CauseEnum(str, Enum):
    soft_decline = "soft_decline"
    hard_decline = "hard_decline"
    gateway_fault = "gateway_fault"
    fraud_filter_block = "fraud_filter_block"
    notification_compliance_block = "notification_compliance_block"

class ActionEnum(str, Enum):
    retry_now = "retry_now"
    retry_scheduled = "retry_scheduled"
    do_not_retry = "do_not_retry"
    reverify_and_reverse = "reverify_and_reverse"
    silent_reschedule = "silent_reschedule"

class TransactionInput(BaseModel):
    status_code: str
    npci_response_code: str
    retry_count_so_far: int
    amount: float
    customer_bank: str
    time_since_last_failure: int

class RootCauseOutput(BaseModel):
    cause: CauseEnum
    confidence: float
    reasoning: str
    recommended_action: ActionEnum

class RetryAlternative(BaseModel):
    window: datetime
    probability: float

class RetryInput(BaseModel):
    failure_cause: CauseEnum
    payment_method: str
    amount: float

class RetryOutput(BaseModel):
    recommended_retry_window: datetime
    predicted_success_probability: float
    ranked_alternative_windows: List[RetryAlternative]

class DunningInput(BaseModel):
    customer_tenure_months: int
    prior_payment_success_rate: float
    amount: float

class DunningOutput(BaseModel):
    recommended_channel: str
    predicted_response_probability: float
    recommended_send_time: datetime

class FalseDeclineInput(BaseModel):
    amount: float
    transaction_velocity: int
    is_known_device: int
    ip_risk_score: float
    merchant_category: str
    transaction_hour: int

class FalseDeclineOutput(BaseModel):
    false_decline_likelihood: float
    recommended_action: str
    contributing_features: List[str]

class PipelineInput(BaseModel):
    transaction: TransactionInput
    payment_method: str

class PipelineOutput(BaseModel):
    root_cause: RootCauseOutput
    retry: Optional[RetryOutput] = None
    dunning: Optional[DunningOutput] = None