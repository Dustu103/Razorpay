'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Zap, 
  ShieldCheck, 
  TrendingDown, 
  CreditCard, 
  Scale, 
  FileCheck, 
  ShieldAlert, 
  Cpu, 
  LayoutDashboard,
  Brain,
  ExternalLink
} from 'lucide-react';

const NAV_ITEMS = [
  { href: '/', label: 'Overview', icon: LayoutDashboard, pillar: 'Dashboard' },
  { href: '/models', label: 'ML Models', icon: Brain, pillar: 'Pillar 1 AI' },
  { href: '/nach', label: 'NACH Shield', icon: ShieldCheck, pillar: 'Pillar 2' },
  { href: '/dropoff', label: 'Causal Drop-Off', icon: TrendingDown, pillar: 'Pillar 3' },
  { href: '/edge-rescue', label: 'Edge Rescue', icon: CreditCard, pillar: 'Pillar 5' },
  { href: '/chargeback', label: 'Disputes', icon: Scale, pillar: 'Pillar 6' },
  { href: '/tax-approvals', label: 'Tax Approvals', icon: FileCheck, pillar: 'Pillar 7' },
  { href: '/compliance', label: 'Compliance', icon: ShieldAlert, pillar: 'Pillar 8' },
  { href: '/npci-governor', label: 'NPCI Governor', icon: Cpu, pillar: 'Pillar 9' },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="header" style={{ position: 'sticky', top: 0, zIndex: 100 }}>
      <div className="header-inner" style={{ maxWidth: '1440px', padding: '0 1.5rem' }}>
        {/* Brand */}
        <Link href="/" className="header-brand" style={{ textDecoration: 'none' }}>
          <div className="header-logo-wrap" style={{
            background: 'linear-gradient(135deg, rgba(129, 140, 248, 0.25), rgba(192, 132, 252, 0.25))',
            boxShadow: '0 0 20px rgba(129, 140, 248, 0.25)'
          }}>
            <Zap size={20} style={{ color: 'var(--indigo)' }} />
          </div>
          <div>
            <div className="header-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>Razorpay AI</span>
              <span style={{
                fontSize: '0.65rem',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                background: 'rgba(129, 140, 248, 0.15)',
                color: 'var(--indigo)',
                border: '1px solid rgba(129, 140, 248, 0.3)',
                padding: '1px 6px',
                borderRadius: '999px',
                fontWeight: 600
              }}>
                9 Pillars
              </span>
            </div>
            <div className="header-sub" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Autonomous Revenue Recovery Ecosystem
            </div>
          </div>
        </Link>

        {/* Navigation items */}
        <nav style={{ 
          display: 'flex', 
          gap: '0.35rem', 
          alignItems: 'center', 
          marginLeft: 'auto', 
          marginRight: '1rem',
          background: 'rgba(255,255,255,0.02)',
          padding: '4px 6px',
          borderRadius: '12px',
          border: '1px solid rgba(255,255,255,0.05)'
        }}>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className="nav-link"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  fontSize: '0.8rem',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? '#FFFFFF' : 'var(--text-muted)',
                  background: isActive ? 'linear-gradient(135deg, rgba(129, 140, 248, 0.2), rgba(192, 132, 252, 0.15))' : 'transparent',
                  border: isActive ? '1px solid rgba(129, 140, 248, 0.35)' : '1px solid transparent',
                  padding: '5px 10px',
                  borderRadius: '8px',
                  textDecoration: 'none',
                  transition: 'all 0.2s ease',
                  boxShadow: isActive ? '0 0 12px rgba(129, 140, 248, 0.15)' : 'none'
                }}
              >
                <Icon size={14} style={{ color: isActive ? 'var(--indigo)' : 'inherit' }} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
