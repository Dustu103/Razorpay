'use client';

import React, { useState, useEffect } from 'react';
import { X, CreditCard, Smartphone, Banknote, ShieldCheck, Tag, ChevronDown, ChevronUp } from 'lucide-react';

interface MockCheckoutModalProps {
  onClose: () => void;
  onEventFired: (eventType: string) => void;
}

export default function MockCheckoutModal({ onClose, onEventFired }: MockCheckoutModalProps) {
  const [sessionId] = useState(() => Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15));
  const [cartValue] = useState(1500);
  const [showTaxes, setShowTaxes] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Send event to ingestion service via Next.js API proxy
  const sendEvent = async (eventType: string) => {
    try {
      await fetch('/api/simulate-checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: Math.random().toString(36).substring(2, 15),
          session_id: sessionId,
          event_type: eventType,
          client_timestamp: new Date().toISOString(),
          cart_value: cartValue
        })
      });
      onEventFired(eventType);
    } catch (e) {
      console.error("Failed to send checkout event:", e);
    }
  };

  // Trigger checkout_started immediately on mount
  useEffect(() => {
    sendEvent('checkout_started');
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleClose = () => {
    // If they saw taxes, it's a price shock abandonment
    if (showTaxes) {
      sendEvent('cart_breakdown_viewed');
    }
    // If they just close it without doing anything, it's a genuine abandonment
    sendEvent('checkout_closed');
    onClose();
  };

  const handleViewTaxes = () => {
    setShowTaxes(!showTaxes);
    if (!showTaxes) {
      sendEvent('cart_breakdown_viewed');
    }
  };

  const simulateVpaFailure = async () => {
    setIsProcessing(true);
    sendEvent('redirect_initiated');
    
    // Simulate loading
    setTimeout(async () => {
      await sendEvent('vpa_validation_failed');
      setIsProcessing(false);
      onClose(); // Auto close on failure to simulate dropoff
    }, 1500);
  };

  return (
    <div className="checkout-overlay">
      <div className="checkout-modal">
        {/* Header */}
        <div className="checkout-header">
          <div className="merchant-info">
            <div className="merchant-logo">RZ</div>
            <div>
              <div className="merchant-name">Acme Electronics</div>
              <div className="merchant-desc">Test Environment</div>
            </div>
          </div>
          <button className="close-btn" onClick={handleClose} disabled={isProcessing}>
            <X size={20} />
          </button>
        </div>

        {/* Order Summary */}
        <div className="order-summary">
          <div className="amount-row">
            <span className="amount-label">Amount to Pay</span>
            <span className="amount-value">₹{(cartValue + (showTaxes ? 270 : 0)).toFixed(2)}</span>
          </div>
          
          <button className="tax-toggle" onClick={handleViewTaxes}>
            View Price Breakdown {showTaxes ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {showTaxes && (
            <div className="tax-breakdown">
              <div className="tax-row">
                <span>Base Amount</span>
                <span>₹{cartValue.toFixed(2)}</span>
              </div>
              <div className="tax-row">
                <span>Shipping</span>
                <span>₹100.00</span>
              </div>
              <div className="tax-row">
                <span>GST (18%)</span>
                <span>₹170.00</span>
              </div>
              <div className="tax-row highlight">
                <span><Tag size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }}/> Price Shock Triggered!</span>
              </div>
            </div>
          )}
        </div>

        {/* Contact Info */}
        <div className="contact-info">
          <div className="contact-label">Contact Details</div>
          <div className="contact-value">test.user@example.com</div>
          <div className="contact-value">+91 9876543210</div>
        </div>

        {/* Payment Methods */}
        <div className="payment-methods">
          <div className="methods-label">Select Payment Method</div>
          
          <button className="method-btn" onClick={simulateVpaFailure} disabled={isProcessing}>
            <div className="method-icon" style={{ background: '#E8F5E9', color: '#2E7D32' }}>
              <Smartphone size={20} />
            </div>
            <div className="method-details">
              <div className="method-name">UPI / QR</div>
              <div className="method-desc">Simulate VPA Validation Failure</div>
            </div>
          </button>

          <button className="method-btn" disabled={true} style={{ opacity: 0.6 }}>
            <div className="method-icon" style={{ background: '#E3F2FD', color: '#1565C0' }}>
              <CreditCard size={20} />
            </div>
            <div className="method-details">
              <div className="method-name">Card</div>
              <div className="method-desc">Visa, MasterCard, RuPay</div>
            </div>
          </button>

          <button className="method-btn" disabled={true} style={{ opacity: 0.6 }}>
            <div className="method-icon" style={{ background: '#FFF3E0', color: '#1565C0' }}>
              <Banknote size={20} />
            </div>
            <div className="method-details">
              <div className="method-name">Netbanking</div>
              <div className="method-desc">All major banks supported</div>
            </div>
          </button>
        </div>

        {/* Footer */}
        <div className="checkout-footer">
          <ShieldCheck size={16} color="#4CAF50" />
          <span>Secured by Razorpay</span>
        </div>

        {isProcessing && (
          <div className="processing-overlay">
            <div className="spinner"></div>
            <div>Processing Payment...</div>
          </div>
        )}
      </div>
      <style dangerouslySetContents={{__html: `
        .checkout-overlay {
          position: fixed; top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
          display: flex; align-items: center; justify-content: center;
          z-index: 9999;
        }
        .checkout-modal {
          background: #ffffff; color: #333333;
          width: 100%; max-width: 400px; border-radius: 12px;
          overflow: hidden; box-shadow: 0 24px 48px rgba(0,0,0,0.2);
          position: relative;
        }
        .checkout-header {
          display: flex; justify-content: space-between; align-items: center;
          padding: 1rem 1.5rem; background: #F8F9FA;
          border-bottom: 1px solid #E0E0E0;
        }
        .merchant-info { display: flex; align-items: center; gap: 0.75rem; }
        .merchant-logo {
          width: 32px; height: 32px; background: var(--indigo); color: white;
          border-radius: 8px; display: flex; align-items: center; justify-content: center;
          font-weight: 700; font-size: 0.85rem;
        }
        .merchant-name { font-weight: 600; font-size: 0.95rem; }
        .merchant-desc { font-size: 0.75rem; color: #666; }
        .close-btn { background: none; border: none; color: #666; cursor: pointer; padding: 4px; }
        .close-btn:hover { color: #000; }
        
        .order-summary { padding: 1.5rem; border-bottom: 1px solid #E0E0E0; }
        .amount-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
        .amount-label { font-size: 0.9rem; color: #555; }
        .amount-value { font-size: 1.5rem; font-weight: 700; color: #111; }
        .tax-toggle {
          background: none; border: none; color: var(--indigo); font-size: 0.85rem;
          display: flex; align-items: center; gap: 4px; cursor: pointer; padding: 0; font-weight: 500;
        }
        .tax-toggle:hover { text-decoration: underline; }
        .tax-breakdown { margin-top: 1rem; padding: 1rem; background: #F5F5F5; border-radius: 8px; font-size: 0.85rem; color: #555; }
        .tax-row { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
        .tax-row:last-child { margin-bottom: 0; }
        .tax-row.highlight { margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid #ddd; color: var(--amber); font-weight: 600; }
        
        .contact-info { padding: 1rem 1.5rem; background: #FAFAFA; border-bottom: 1px solid #E0E0E0; }
        .contact-label { font-size: 0.75rem; color: #777; text-transform: uppercase; font-weight: 600; margin-bottom: 0.25rem; }
        .contact-value { font-size: 0.85rem; color: #333; margin-bottom: 0.25rem; }
        
        .payment-methods { padding: 1.5rem; }
        .methods-label { font-size: 0.85rem; font-weight: 600; color: #444; margin-bottom: 1rem; }
        .method-btn {
          width: 100%; display: flex; align-items: center; gap: 1rem;
          padding: 1rem; background: #fff; border: 1px solid #E0E0E0; border-radius: 8px;
          margin-bottom: 0.75rem; cursor: pointer; transition: all 0.2s; text-align: left;
        }
        .method-btn:hover:not(:disabled) { border-color: var(--indigo); box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .method-icon { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .method-name { font-weight: 600; font-size: 0.95rem; color: #222; }
        .method-desc { font-size: 0.75rem; color: #666; margin-top: 2px; }
        
        .checkout-footer {
          padding: 1rem; text-align: center; display: flex; align-items: center; justify-content: center;
          gap: 6px; font-size: 0.75rem; color: #666; background: #F8F9FA;
        }
        
        .processing-overlay {
          position: absolute; top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(255,255,255,0.9); display: flex; flex-direction: column;
          align-items: center; justify-content: center; font-weight: 600; color: var(--indigo);
        }
        .spinner {
          width: 32px; height: 32px; border: 3px solid rgba(0,0,0,0.1);
          border-top-color: var(--indigo); border-radius: 50%;
          animation: spin 1s linear infinite; margin-bottom: 1rem;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}} />
    </div>
  );
}
