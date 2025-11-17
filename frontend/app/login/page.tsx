'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { GlassCard } from '../../components/GlassCard';
import { login } from '../../lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(username, password);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <GlassCard title="Welcome back" icon="👋">
      <form onSubmit={submit} style={{ display: 'grid', gap: 14 }}>
        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ color: 'var(--text-secondary)' }}>Username</span>
          <input
            style={{ padding: '12px 14px', borderRadius: 12, border: '1px solid var(--glass-border)', background: 'rgba(255,255,255,0.05)', color: 'var(--text-primary)' }}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ color: 'var(--text-secondary)' }}>Password</span>
          <input
            type="password"
            style={{ padding: '12px 14px', borderRadius: 12, border: '1px solid var(--glass-border)', background: 'rgba(255,255,255,0.05)', color: 'var(--text-primary)' }}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <div className="badge warn">{error}</div>}
        <button className="button-primary" type="submit" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </GlassCard>
  );
}
