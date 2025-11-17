'use client';

import useSWR from 'swr';
import Link from 'next/link';
import { GlassCard } from '../../components/GlassCard';
import { fetchSession, fetchTorrents } from '../../lib/api';

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: '#c7f1e0',
    downloading: '#e5f2ff',
    uploading: '#fff3c2',
    failed: '#ffd6d6',
    queued: 'rgba(255,255,255,0.15)',
  };
  return (
    <span className="badge" style={{ background: colors[status] || 'rgba(255,255,255,0.15)' }}>
      {status}
    </span>
  );
}

export default function DashboardPage() {
  const { data: session } = useSWR('session', fetchSession);
  const { data: torrents } = useSWR('torrents', fetchTorrents, { refreshInterval: 5000 });

  return (
    <div className="grid" style={{ gap: 18 }}>
      <GlassCard
        title={`Hi ${session?.username || 'there'}`}
        icon="🛰️"
        action={
          <div className="hero-actions">
            <Link className="button-ghost" href="/">
              Home
            </Link>
            <Link className="button-primary" href="/torrents/1">
              Try details view
            </Link>
          </div>
        }
      >
        <div className="grid two">
          <div>
            <div className="metric-value">{session?.daily_usage_gb ?? '–'} GB</div>
            <div className="metric-label">Used today</div>
          </div>
          <div>
            <div className="metric-value">{session?.daily_limit_gb ?? '∞'} GB</div>
            <div className="metric-label">Daily limit</div>
          </div>
        </div>
      </GlassCard>

      <GlassCard title="Active Torrents" icon="📡">
        {(torrents || []).map((t: any) => (
          <div key={t.id} className="torrent-row">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <StatusBadge status={t.status} />
                <Link href={`/torrents/${t.id}`} style={{ fontWeight: 700 }}>
                  {t.name}
                </Link>
              </div>
              <div className="progress-shell" aria-hidden>
                <div className="progress-bar" style={{ width: `${t.progress ?? 0}%` }} />
              </div>
            </div>
            <div style={{ textAlign: 'right', color: 'var(--text-secondary)' }}>
              {t.download_rate ? `${(t.download_rate / 1024 / 1024).toFixed(2)} MB/s` : 'waiting'}
            </div>
            <div style={{ textAlign: 'right', color: 'var(--text-secondary)' }}>
              {t.eta_seconds ? `${Math.round(t.eta_seconds / 60)} min` : '—'}
            </div>
          </div>
        ))}
        {!torrents?.length && <div style={{ color: 'var(--text-secondary)' }}>No torrents yet.</div>}
      </GlassCard>
    </div>
  );
}
