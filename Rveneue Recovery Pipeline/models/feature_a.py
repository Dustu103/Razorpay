import json
from langchain_google_genai import ChatGoogleGenerativeAI
from config import GOOGLE_API_KEY, LLM_MODEL
from schemas import RootCauseOutput, TransactionInput, CauseEnum, ActionEnum

class FeatureAClassifier:
    def __init__(self):
        self.model = None
        if GOOGLE_API_KEY and GOOGLE_API_KEY != "your-google-api-key-here":
            llm = ChatGoogleGenerativeAI(
                model=LLM_MODEL,
                google_api_key=GOOGLE_API_KEY,
                temperature=0.0
            )
            self.model = llm.with_structured_output(RootCauseOutput)

    def classify(self, tx: TransactionInput) -> RootCauseOutput:
        if not self.model:
            return self._fallback_classify(tx)
        
        system_prompt = (
            "You are an AI Payment Root-Cause Classifier. Determine the precise failure cause and recommended action. "
            "Determine the cause and recommended action from the transaction context. Give few-shot examples:\n"
            "Input: status_code=TIMEOUT, npci_response_code=05, retry_count_so_far=1, amount=2500, customer_bank=HDFC, time_since_last_failure=120\n"
            "Output: cause=gateway_fault, confidence=0.91, reasoning='Transient timeout with low retry count', recommended_action=retry_now\n\n"
            "Input: status_code=CARD_BLOCKED, npci_response_code=51, retry_count_so_far=1, amount=500, customer_bank=ICICI, time_since_last_failure=0\n"
            "Output: cause=hard_decline, confidence=0.98, reasoning='Card permanently restricted', recommended_action=do_not_retry\n\n"
            "Input: status_code=COMPLIANCE_HOLD, npci_response_code=99, retry_count_so_far=0, amount=10000, customer_bank=SBI, time_since_last_failure=0\n"
            "Output: cause=notification_compliance_block, confidence=0.95, reasoning='Missing required KYC compliance verification', recommended_action=silent_reschedule"
        )
        
        try:
            prompt = f"{system_prompt}\n\nInput Transaction Context:\n{tx.model_dump_json()}"
            return self.model.invoke(prompt)
        except Exception:
            return self._fallback_classify(tx)

    def _fallback_classify(self, tx: TransactionInput) -> RootCauseOutput:
        status = tx.status_code.upper()
        code = tx.npci_response_code
        
        if "BLOCK" in status or "FRAUD" in status or code in ["34", "59", "93"]:
            return RootCauseOutput(
                cause=CauseEnum.fraud_filter_block,
                confidence=0.90,
                reasoning="Fallback: Flagged as highly suspicious by fraud patterns",
                recommended_action=ActionEnum.do_not_retry
            )
        elif "COMPLIANCE" in status or "COMPLY" in status or code == "88":
            return RootCauseOutput(
                cause=CauseEnum.notification_compliance_block,
                confidence=0.88,
                reasoning="Fallback: Transaction halted due to lack of standard compliant notifications",
                recommended_action=ActionEnum.silent_reschedule
            )
        elif "TIMEOUT" in status or "GATEWAY" in status or code in ["91", "92", "96"]:
            return RootCauseOutput(
                cause=CauseEnum.gateway_fault,
                confidence=0.85,
                reasoning="Fallback: Gateway timed out or is temporarily unavailable",
                recommended_action=ActionEnum.retry_now if tx.retry_count_so_far < 2 else ActionEnum.retry_scheduled
            )
        elif "DECLINE" in status or code in ["05", "51", "61"]:
            if code == "51" or tx.retry_count_so_far >= 3:
                return RootCauseOutput(
                    cause=CauseEnum.hard_decline,
                    confidence=0.87,
                    reasoning="Fallback: Insufficient funds or permanent issuer hard rejection",
                    recommended_action=ActionEnum.do_not_retry
                )
            else:
                return RootCauseOutput(
                    cause=CauseEnum.soft_decline,
                    confidence=0.82,
                    reasoning="Fallback: Temporary soft decline from bank server limits",
                    recommended_action=ActionEnum.retry_scheduled
                )
        else:
            return RootCauseOutput(
                cause=CauseEnum.soft_decline,
                confidence=0.75,
                reasoning="Fallback: Unmapped code classified as retryable soft decline",
                recommended_action=ActionEnum.retry_scheduled
            )