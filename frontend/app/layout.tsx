import type { Metadata } from 'next';
import { Zap } from 'lucide-react';
import './globals.css';

export const metadata: Metadata = {
  title: 'Razorpay Classifier Inspector — Feature 1',
  description: 'Audit and inspect payment failure root-cause classifications — Feature 1 Pillar B Diagnose.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="header">
          <div className="header-inner">
            <div className="header-brand">
              <div className="header-logo-wrap">
                <Zap size={20} style={{ color: 'var(--blue)' }} />
              </div>
              <div>
                <div className="header-title">Classifier Inspector</div>
                <div className="header-sub">Feature 1 · Pillar B — Diagnose</div>
              </div>
            </div>
            <div className="header-right">
              <span className="header-badge">Razorpay AI Buildathon 2026</span>
              <div className="header-dot" title="Live" />
            </div>
          </div>
        </header>
        <main className="main-content">
          {children}
        </main>
      </body>
    </html>
  );
}
