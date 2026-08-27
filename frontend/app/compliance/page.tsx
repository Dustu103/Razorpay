import ComplianceScanner from '@/components/ComplianceScanner';

export const metadata = {
  title: 'Compliance Scanner - Razorpay',
};

export default function CompliancePage() {
  return (
    <div style={{ maxWidth: '800px', margin: '2rem auto' }}>
      <h1 style={{ marginBottom: '2rem', fontSize: '1.5rem', fontWeight: 600 }}>
        UX Compliance Scanner
      </h1>
      <ComplianceScanner />
    </div>
  );
}
