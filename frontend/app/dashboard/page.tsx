'use client';

import { useEffect, useState, FormEvent } from 'react';
import { api } from '../../lib/api';
import { useRouter } from 'next/navigation';

interface UserShape {
  id: number;
  username: string;
  email: string;
  is_admin: boolean;
  plan: {
    type: string;
    name: string;
    expires_at: string | null;
    usage_today_gb: number;
    limit_today_gb: number;
    features: string[];
  };
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserShape | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [form, setForm] = useState({ source_type: 'torrent', magnet_link: '', source_url: '', save_folder: '' });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .me()
      .then((res) => {
        if (!res.authenticated) {
          router.push('/login');
        } else {
          setUser(res.user);
          refreshJobs();
        }
      })
      .catch(() => router.push('/login'));
  }, [router]);

  const refreshJobs = async () => {
    const res = await api.listTorrents();
    setJobs(res.items || []);
  };

  const createJob = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const payload: any = { source_type: form.source_type, save_folder: form.save_folder };
      if (form.source_type === 'torrent') {
        payload.magnet_link = form.magnet_link;
      } else {
        payload.source_url = form.source_url;
      }
      await api.createTorrent(payload);
      await refreshJobs();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="dashboard-grid">
      <div className="glass" style={{ padding: 20 }}>
        <h2>Plan overview</h2>
        {user && (
          <>
            <p>{user.plan.name} plan ({user.plan.type === 'paid' ? 'Priority speed + support' : 'Community'})</p>
            <p>
              Usage today: {user.plan.usage_today_gb} GB / {user.plan.limit_today_gb} GB
              {user.plan.expires_at ? ` · Expires ${user.plan.expires_at}` : ''}
            </p>
          </>
        )}
      </div>
      <div className="glass" style={{ padding: 20 }}>
        <h2>Add job</h2>
        {error && <p className="error-text">{error}</p>}
        <form onSubmit={createJob} className="form-grid">
          <select value={form.source_type} onChange={(e) => setForm({ ...form, source_type: e.target.value })}>
            <option value="torrent">Torrent magnet</option>
            <option value="mega">Mega.nz</option>
          </select>
          {form.source_type === 'torrent' ? (
            <input
              placeholder="Magnet link"
              value={form.magnet_link}
              onChange={(e) => setForm({ ...form, magnet_link: e.target.value })}
            />
          ) : (
            <input
              placeholder="Mega.nz URL"
              value={form.source_url}
              onChange={(e) => setForm({ ...form, source_url: e.target.value })}
            />
          )}
          <input
            placeholder="Save folder name"
            value={form.save_folder}
            onChange={(e) => setForm({ ...form, save_folder: e.target.value })}
          />
          <button className="button-primary" type="submit">
            {form.source_type === 'torrent' ? 'Add Torrent' : 'Add Mega.nz'}
          </button>
        </form>
      </div>
      <div className="glass" style={{ padding: 20 }}>
        <h2>Recent jobs</h2>
        <div className="jobs-grid">
          {jobs.map((job) => (
            <div key={job.id} className="job-card">
              <div className="job-title">{job.name || job.magnet_link || job.source_url}</div>
              <div className="job-status">Status: {job.status}</div>
              <div className="job-meta">Progress: {Math.round(job.progress || 0)}%</div>
              {job.drive_folder_url && <a href={job.drive_folder_url}>Drive link</a>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
