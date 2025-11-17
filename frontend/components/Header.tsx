import Link from 'next/link';

export function Header() {
  return (
    <header className="header-rail">
      <div>
        <div className="pill">
          <span>⚡</span>
          <span className="section-label">Liquid glass experience</span>
        </div>
        <h1 className="hero-title">Torrent2Drive — new glass dashboard</h1>
        <p className="hero-subtitle">
          A premium, Apple-inspired glassmorphic shell for your torrents. Track live speeds, ETA, TMDB movie art, and manage invites
          in a single shimmering surface.
        </p>
        <div className="hero-actions">
          <Link href="/dashboard" className="button-primary">
            Launch dashboard
          </Link>
          <Link href="/login" className="button-ghost">
            Sign in
          </Link>
        </div>
      </div>
      <div className="glass" style={{ padding: '18px 16px', minWidth: 260 }}>
        <div className="section-label" style={{ color: '#c0d5ff', marginBottom: 8 }}>
          Highlights
        </div>
        <div style={{ display: 'grid', gap: 10 }}>
          <div className="pill" style={{ width: 'fit-content' }}>
            🎬 TMDB posters & ratings
          </div>
          <div className="pill" style={{ width: 'fit-content' }}>
            📈 Live speed + ETA
          </div>
          <div className="pill" style={{ width: 'fit-content' }}>
            🔒 Invite controls fixed
          </div>
        </div>
      </div>
    </header>
  );
}
