import os
import json
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Mandate Compliance Scanner API")

# Allow frontend to call directly if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class ScreenElement(BaseModel):
    id: str
    type: str
    text: Optional[str] = None
    state: Optional[str] = None # e.g. "pre-checked", "hidden"

class ScreenFlow(BaseModel):
    screen_name: str
    elements: List[ScreenElement]

class ComplianceRequest(BaseModel):
    flow: List[ScreenFlow]

class Violation(BaseModel):
    screen_name: str
    rule_broken: str
    severity: str # "High", "Medium", "Low"
    fix_suggestion: str

class ComplianceResponse(BaseModel):
    is_compliant: bool
    violations: List[Violation]

SYSTEM_PROMPT = """
You are a strict compliance auditor for the Reserve Bank of India (RBI).
Your job is to analyze a JSON representation of a payment mandate/subscription UX flow.
You must identify if the flow violates any of the 5 following RBI rules regarding "dark patterns":
1. False Urgency (e.g., fake countdown timers)
2. Pre-checked consent boxes
3. Hidden or hard-to-find cancellation buttons
4. Forced product bundling
5. Obscured terms and conditions

Analyze the input flow and respond strictly with a valid JSON object matching this schema:
{
  "is_compliant": boolean,
  "violations": [
    {
      "screen_name": string,
      "rule_broken": string,
      "severity": "High" | "Medium" | "Low",
      "fix_suggestion": string
    }
  ]
}
If no violations are found, return is_compliant: true and an empty violations list.
Do NOT return any markdown formatting or text outside the JSON object.
"""

@app.post("/api/v1/scan-compliance", response_model=ComplianceResponse)
async def scan_compliance(request: ComplianceRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set in environment.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "groq/compound",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.model_dump_json()}
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        content = result['choices'][0]['message']['content']
        # Strip potential markdown code blocks
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        parsed_content = json.loads(content.strip())
        return parsed_content

    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'response') and getattr(e, 'response') is not None:
            error_msg += f" Response Body: {e.response.text}"
        print(f"Groq API Error: {error_msg}. Falling back to Gemini...")
        
        # GEMINI FALLBACK
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
             raise HTTPException(status_code=502, detail=f"Groq failed and GEMINI_API_KEY is not set.")
             
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
        gemini_payload = {
            "contents": [{
                "parts": [{"text": SYSTEM_PROMPT + "\n\nJSON Flow Data:\n" + request.model_dump_json()}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }
        
        try:
             gemini_res = requests.post(gemini_url, json=gemini_payload, timeout=15)
             gemini_res.raise_for_status()
             gemini_data = gemini_res.json()
             gemini_content = gemini_data['candidates'][0]['content']['parts'][0]['text']
             return json.loads(gemini_content.strip())
        except Exception as gemini_e:
             gemini_err = str(gemini_e)
             if hasattr(gemini_e, 'response') and getattr(gemini_e, 'response') is not None:
                 gemini_err += f" Body: {gemini_e.response.text}"
             print(f"Gemini API Error: {gemini_err}")
             raise HTTPException(status_code=502, detail=f"Both Groq and Gemini failed. Groq: {error_msg} | Gemini: {gemini_err}")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "compliance-scanner"}
