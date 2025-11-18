'use client';

import { FormEvent, useState } from 'react';
import { api } from '../../lib/api';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email_or_username: '', password: '' });
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.login(form.email_or_username, form.password);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="glass" style={{ padding: 24 }}>
      <h2>Log in</h2>
      {error && <p className="error-text">{error}</p>}
      <form onSubmit={onSubmit} className="form-grid">
        <input
          placeholder="Email or username"
          value={form.email_or_username}
          onChange={(e) => setForm({ ...form, email_or_username: e.target.value })}
        />
        <input
          placeholder="Password"
          type="password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
        <button className="button-primary" type="submit">
          Sign in
        </button>
      </form>
      <p style={{ marginTop: 12 }}>
        <Link href="/password-reset">Forgot password?</Link>
      </p>
    </div>
  );
}
