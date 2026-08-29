from typing import Optional
from schemas import TransactionInput, PipelineInput, PipelineOutput, RetryInput, DunningInput
from models import FeatureAClassifier,FeatureBModel, FeatureCModel


class RecoveryPipeline:
    def __init__(self):
        self.classifier = FeatureAClassifier()
        self.retry_model = FeatureBModel()
        self.dunning_model = FeatureCModel()

    def process(self, payload: PipelineInput, customer_tenure: int = 12, prior_success_rate: float = 0.8) -> PipelineOutput:
        rc_result = self.classifier.classify(payload.transaction)
        
        retry_result = None
        dunning_result = None
        
        if rc_result.recommended_action in ["retry_now", "retry_scheduled"]:
            r_input = RetryInput(
                failure_cause=rc_result.cause,
                payment_method=payload.payment_method,
                amount=payload.transaction.amount
            )
            retry_result = self.retry_model.predict(r_input)
            
            d_input = DunningInput(
                customer_tenure_months=customer_tenure,
                prior_payment_success_rate=prior_success_rate,
                amount=payload.transaction.amount
            )
            dunning_result = self.dunning_model.predict(d_input)
        else:
            d_input = DunningInput(
                customer_tenure_months=customer_tenure,
                prior_payment_success_rate=prior_success_rate,
                amount=payload.transaction.amount
            )
            dunning_result = self.dunning_model.predict(d_input)
            
        return PipelineOutput(
            root_cause=rc_result,
            retry=retry_result,
            dunning=dunning_result
        )