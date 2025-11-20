'use client';

import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { useRouter } from 'next/navigation';

export default function AdminPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<any>(null);

  useEffect(() => {
    api
      .me()
      .then((res) => {
        if (!res.authenticated || !res.user.is_admin) {
          router.push('/login');
          return;
        }
        fetchOverview();
      })
      .catch(() => router.push('/login'));
  }, [router]);

  const fetchOverview = async () => {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5000'}/api/admin/overview`, {
      credentials: 'include',
    });
    const data = await res.json();
    setOverview(data);
  };

  return (
    <div className="glass" style={{ padding: 24 }}>
      <h2>Admin overview</h2>
      {overview ? (
        <div className="admin-grid">
          <div className="stat">Total users: {overview.user_counts.total}</div>
          <div className="stat">Free users: {overview.user_counts.free}</div>
          <div className="stat">Paid users: {overview.user_counts.paid}</div>
          <div className="stat">Active free jobs: {overview.active_jobs.free}</div>
          <div className="stat">Active paid jobs: {overview.active_jobs.paid}</div>
          <div className="stat">Bandwidth today: {overview.bandwidth_today_gb.total} GB</div>
        </div>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  );
}
