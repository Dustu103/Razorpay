import sys
sys.path.append('.')

from app.models.b2b_agent import B2BAgentModel, B2BInvoiceInput

agent = B2BAgentModel()

print("--- Test 1: MSME > 45 days late (Should trigger Sec 43B) ---")
data1 = B2BInvoiceInput(id="INV-001", customer_name="Test Corp", amount_due=10000.0, is_msme_registered=True, days_late=46)
res1 = agent.predict(data1)
print(f"Action: {res1.action}")
print(f"Rule: {res1.tax_rule_triggered}")
print(f"Email:\n{res1.draft_email_body}\n")

print("--- Test 2: Non-MSME > 180 days late (Should trigger standard escalation since Rule 37 was removed) ---")
data2 = B2BInvoiceInput(id="INV-002", customer_name="Big Corp", amount_due=50000.0, is_msme_registered=False, days_late=181)
res2 = agent.predict(data2)
print(f"Action: {res2.action}")
print(f"Rule: {res2.tax_rule_triggered}")
print(f"Email:\n{res2.draft_email_body}\n")
