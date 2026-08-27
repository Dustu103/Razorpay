'use client';

import { useState } from 'react';
import { Loader2, ShieldCheck, ShieldAlert, Code } from 'lucide-react';

export default function ComplianceScanner() {
  const [jsonInput, setJsonInput] = useState(`{
  "flow": [
    {
      "screen_name": "checkout_step_1",
      "elements": [
        { "id": "btn_pay", "type": "button", "text": "Pay Now (Hurry, 5 mins left!)" },
        { "id": "chk_subscribe", "type": "checkbox", "state": "pre-checked", "text": "Subscribe to premium" }
      ]
    },
    {
      "screen_name": "cancellation_settings",
      "elements": [
        { "id": "btn_cancel", "type": "button", "state": "hidden", "text": "Cancel Subscription" }
      ]
    }
  ]
}`);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleScan = async () => {
    setLoading(true);
    setError('');
    setResult(null);

    try {
      // Validate JSON first
      const payload = JSON.parse(jsonInput);
      
      const res = await fetch('http://localhost:3004/api/v1/scan-compliance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`API Error: ${res.statusText}`);
      }

      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Failed to scan compliance');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="simulator-panel">
      <div className="panel-header">
        <ShieldCheck className="icon purple" />
        <h2>Mandate Compliance Scanner (Feature 2)</h2>
      </div>

      <div className="panel-content">
        <p style={{marginBottom: '1rem', color: '#64748b'}}>
          Validate a business's UX flow against the Feb 2026 RBI Guidelines for recurring mandates.
        </p>

        <div className="json-editor-wrap">
          <div className="editor-header">
            <Code size={14} />
            <span>Screen JSON Definition</span>
          </div>
          <textarea 
            className="json-textarea"
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
            spellCheck="false"
            rows={15}
          />
        </div>

        <div style={{marginTop: '1rem', display: 'flex', gap: '1rem', alignItems: 'center'}}>
          <button className="btn primary" onClick={handleScan} disabled={loading}>
            {loading ? <Loader2 className="spin" size={16} /> : <ShieldCheck size={16} />}
            {loading ? 'Scanning...' : 'Scan Flow for RBI Violations'}
          </button>
        </div>

        {error && (
          <div className="error-message" style={{marginTop: '1rem', padding: '1rem', backgroundColor: '#fee2e2', color: '#b91c1c', borderRadius: '6px'}}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {result && (
          <div className="scan-results" style={{marginTop: '2rem', borderTop: '1px solid #e2e8f0', paddingTop: '1.5rem'}}>
            <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem'}}>
              {result.is_compliant ? (
                <><ShieldCheck size={24} color="#10b981" /> <h3 style={{color: '#10b981', margin: 0}}>Fully Compliant</h3></>
              ) : (
                <><ShieldAlert size={24} color="#ef4444" /> <h3 style={{color: '#ef4444', margin: 0}}>Compliance Violations Detected</h3></>
              )}
            </div>

            <div style={{display: 'flex', gap: '1rem', marginBottom: '1.5rem'}}>
              <span className="badge" style={{background: '#e2e8f0', color: '#475569', fontSize: '0.8rem', padding: '4px 10px', borderRadius: '16px'}}>
                Layer 1 (Deterministic): {result.layer1_violations || 0}
              </span>
              <span className="badge" style={{background: '#ede9fe', color: '#6d28d9', fontSize: '0.8rem', padding: '4px 10px', borderRadius: '16px'}}>
                Layer 2 (LLM): {result.layer2_violations || 0}
              </span>
            </div>

            {result.violations && result.violations.length > 0 && (
              <div className="violations-list" style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
                {result.violations.map((v: any, idx: number) => (
                  <div key={idx} className="violation-card" style={{
                    padding: '1rem', 
                    borderRadius: '8px', 
                    borderLeft: \`4px solid \${v.severity === 'High' ? '#ef4444' : v.severity === 'Medium' ? '#f59e0b' : '#3b82f6'}\`,
                    backgroundColor: '#f8fafc'
                  }}>
                    <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
                      <strong>Screen: {v.screen_name}</strong>
                      <div style={{display: 'flex', gap: '0.5rem'}}>
                        <span className="badge" style={{fontSize: '0.7rem', padding: '2px 8px', borderRadius: '12px', background: v.detected_by === 'layer1_deterministic' ? '#f1f5f9' : '#ede9fe', color: v.detected_by === 'layer1_deterministic' ? '#64748b' : '#6d28d9'}}>
                          {v.detected_by === 'layer1_deterministic' ? 'Layer 1' : 
                           v.detected_by === 'layer2_llm_ensemble_consensus' ? 'Layer 2 (Groq + Gemini Consensus)' :
                           v.detected_by === 'layer2_llm_groq' ? 'Layer 2 (Groq Only)' :
                           v.detected_by === 'layer2_llm_gemini' ? 'Layer 2 (Gemini Only)' : 'Layer 2 (LLM)'}
                        </span>
                        <span className={\`badge badge-\${v.severity.toLowerCase()}\`} style={{fontSize: '0.75rem', padding: '2px 8px', borderRadius: '12px', background: v.severity==='High'?'#fee2e2':v.severity==='Medium'?'#fef3c7':'#dbeafe', color: v.severity==='High'?'#991b1b':v.severity==='Medium'?'#92400e':'#1e40af'}}>
                          {v.severity} Severity
                        </span>
                      </div>
                    </div>
                    <div style={{marginBottom: '0.5rem'}}><strong>Rule Broken:</strong> {v.rule_broken}</div>
                    <div style={{color: '#059669', fontSize: '0.9rem'}}><strong>Suggested Fix:</strong> {v.fix_suggestion}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
