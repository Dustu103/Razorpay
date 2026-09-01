import type { Metadata } from 'next';
import { Zap } from 'lucide-react';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'Razorpay Revenue Recovery Ecosystem',
  description: '4-Pillar Architecture: Prevent, Diagnose, Recover, Escalate.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="header">
          <div className="header-inner">
            <div className="header-brand">
              <div className="header-logo-wrap">
                <Zap size={20} style={{ color: 'var(--indigo)' }} />
              </div>
              <div>
                <div className="header-title">Revenue Recovery</div>
                <div className="header-sub">4-Pillar AI Ecosystem</div>
              </div>
            </div>

            <nav style={{ display: 'flex', gap: '1.75rem', alignItems: 'center', marginLeft: 'auto', marginRight: '2rem' }}>
              <Link href="/" style={{ color: 'var(--text-primary)', textDecoration: 'none', fontWeight: 500, fontSize: '0.9rem', transition: 'color 0.2s' }} className="nav-link">
                Dashboard
              </Link>
              <Link href="/compliance" style={{ color: 'var(--text-primary)', textDecoration: 'none', fontWeight: 500, fontSize: '0.9rem', transition: 'color 0.2s' }} className="nav-link">
                Compliance Scanner
              </Link>
              <Link href="/chargeback" style={{ color: 'var(--text-primary)', textDecoration: 'none', fontWeight: 500, fontSize: '0.9rem', transition: 'color 0.2s' }} className="nav-link">
                Chargebacks
              </Link>
              <Link href="/tax-approvals" style={{ color: 'var(--indigo)', textDecoration: 'none', fontWeight: 600, fontSize: '0.9rem', transition: 'color 0.2s' }} className="nav-link">
                Tax Approvals
              </Link>
            </nav>
            
            <div className="header-right">
              <span className="header-badge">AI Buildathon 2026</span>
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
