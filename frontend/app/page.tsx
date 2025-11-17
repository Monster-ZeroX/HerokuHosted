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
          <p className="metric-label">Surfaced directly from the Flask API for precision reads.</p>
        </GlassCard>
        <GlassCard title="Invite Control" icon="🔑">
          <div className="metric-value">Reactivate & tune limits</div>
          <p className="metric-label">Manage invites without modal flicker in the admin console.</p>
        </GlassCard>
      </div>
      <div style={{ marginTop: 22 }}>
        <GlassCard title="Get started" icon="🎬" action={<Link className="button-primary" href="/dashboard">Open dashboard</Link>}>
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
            Switch to the premium Liquid Glass interface backed by Next.js while the Flask API powers downloads and TMDB
            metadata for movie torrents.
          </p>
        </GlassCard>
      </div>
    </>
  );
}
