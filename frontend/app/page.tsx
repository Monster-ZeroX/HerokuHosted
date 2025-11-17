import { Header } from '../components/Header';
import { GlassCard } from '../components/GlassCard';
import Link from 'next/link';

export default function HomePage() {
  return (
    <>
      <Header />
      <div className="grid two">
        <GlassCard title="Realtime Speed" icon="⚡">
          <div className="metric-value">Live download + ETA</div>
          <p className="metric-label">Pulls from the Flask API with second-level polling to keep numbers fresh.</p>
        </GlassCard>
        <GlassCard title="Invite Control" icon="🔑">
          <div className="metric-value">Reactivate & tune limits</div>
          <p className="metric-label">Manage invites without modal flicker in the admin console.</p>
        </GlassCard>
      </div>
      <div style={{ marginTop: 22 }}>
        <GlassCard
          title="Go glassy"
          icon="🪩"
          action={
            <div className="hero-actions">
              <Link className="button-primary" href="/dashboard">
                Open dashboard
              </Link>
              <Link className="button-ghost" href="/torrents/1">
                View example torrent
              </Link>
            </div>
          }
        >
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
            Switch to the liquid-glass interface backed by Next.js. The right rail in torrent details lights up with TMDB metadata when
            movies are detected, leaving other torrent types clean.
          </p>
        </GlassCard>
      </div>
    </>
  );
}
