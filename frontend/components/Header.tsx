import Link from 'next/link';

export function Header() {
  return (
    <header style={{ marginBottom: 28 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <p style={{ margin: 0, color: 'var(--text-secondary)' }}>Torrent2Drive</p>
          <h1 className="hero-title">Liquid Glass Control Center</h1>
          <p className="hero-subtitle">
            Monitor torrents, inspect speeds, and manage invites with a premium glass UI powered by Next.js.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <Link href="/login" className="button-ghost">Login</Link>
          <Link href="/dashboard" className="button-primary">Dashboard</Link>
        </div>
      </div>
    </header>
  );
}
