'use client';

import { useParams } from 'next/navigation';
import useSWR from 'swr';
import Link from 'next/link';
import { GlassCard } from '../../../components/GlassCard';
import { api } from '../../../lib/api';

function prettySize(bytes?: number) {
  if (!bytes) return '—';
  const gb = bytes / 1024 / 1024 / 1024;
  return `${gb.toFixed(2)} GB`;
}

export default function TorrentDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const { data: torrent } = useSWR(
    id ? `torrent-${id}` : null,
    async () => {
      if (!id) return null;
      const data = await api.getTorrent(Number(id));
      return (data as any).job ?? data;
    },
    { refreshInterval: 5000 }
  );

  if (!id) return null;

  return (
    <div className="grid" style={{ gap: 18 }}>
      <GlassCard title={torrent?.name || 'Loading...'} icon="🎞️" action={<Link className="button-ghost" href="/dashboard">Back</Link>}>
        <div style={{ display: 'grid', gap: 12 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <span className="badge soft">{torrent?.status || 'pending'}</span>
            <span style={{ color: 'var(--text-secondary)' }}>Progress {torrent?.progress?.toFixed?.(1) ?? 0}%</span>
          </div>
          <div className="progress-shell">
            <div className="progress-bar" style={{ width: `${torrent?.progress ?? 0}%` }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
            <div>
              <div className="metric-label">Speed</div>
              <div className="metric-value">{torrent?.download_rate ? `${(torrent.download_rate / 1024 / 1024).toFixed(2)} MB/s` : '—'}</div>
            </div>
            <div>
              <div className="metric-label">ETA</div>
              <div className="metric-value">{torrent?.eta_seconds ? `${Math.round(torrent.eta_seconds / 60)} min` : '—'}</div>
            </div>
            <div>
              <div className="metric-label">Size</div>
              <div className="metric-value">{prettySize(torrent?.total_size)}</div>
            </div>
          </div>
        </div>
      </GlassCard>

      <div className="grid two">
        <GlassCard title="Files" icon="📁">
          {(torrent?.files || []).map((file: any) => (
            <div key={file.id} style={{ padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <div style={{ fontWeight: 600 }}>{file.file_path}</div>
              <div className="metric-label">{prettySize(file.file_size)}</div>
            </div>
          ))}
          {!torrent?.files?.length && <div style={{ color: 'var(--text-secondary)' }}>Waiting for file list…</div>}
        </GlassCard>

        {torrent?.tmdb ? (
          <GlassCard title="Movie intel" icon="🍿">
            <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 16, alignItems: 'center' }}>
              {torrent.tmdb.poster_url && <img className="poster" src={torrent.tmdb.poster_url} alt={torrent.tmdb.title} />}
              <div style={{ display: 'grid', gap: 6 }}>
                <div className="metric-value" style={{ fontSize: '1.4rem' }}>
                  {torrent.tmdb.title}
                </div>
                <div className="metric-label">{torrent.tmdb.release_date}</div>
                <div className="badge success" style={{ width: 'fit-content' }}>
                  ⭐ {torrent.tmdb.rating}
                </div>
                <p style={{ color: 'var(--text-secondary)', margin: 0 }}>{torrent.tmdb.overview}</p>
              </div>
            </div>
          </GlassCard>
        ) : (
          <GlassCard title="Movie intel" icon="🍿">
            <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
              No TMDB data for this torrent yet. Movie posters and ratings will appear automatically for film downloads.
            </p>
          </GlassCard>
        )}
      </div>
    </div>
  );
}
