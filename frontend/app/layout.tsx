import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'Razorpay Revenue Recovery Ecosystem',
  description: '9-Pillar Autonomous AI Ecosystem: Diagnostic MoE, NACH Mandate Shield, Causal Drop-Off, BNPL Edge, Dispute Defense, B2B Tax Lever, RBI Scanner, and NPCI Governor.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        <main className="main-content">
          {children}
        </main>
      </body>
    </html>
  );
}
