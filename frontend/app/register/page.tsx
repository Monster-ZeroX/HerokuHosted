'use client';

import { FormEvent, useState } from 'react';
import { api } from '../../lib/api';
import Link from 'next/link';

export default function RegisterPage() {
  const [step, setStep] = useState<'start' | 'verify'>('start');
  const [form, setForm] = useState({ username: '', email: '', password: '', code: '' });
  const [message, setMessage] = useState<string | null>(null);

  const handleStart = async (e: FormEvent) => {
    e.preventDefault();
    const { username, email, password } = form;
    const res = await api.registerStart({ username, email, password });
    setMessage(res.message);
    setStep('verify');
  };

  const handleVerify = async (e: FormEvent) => {
    e.preventDefault();
    await api.registerVerify({ email: form.email, code: form.code });
    setMessage('Registration complete. You are now signed in.');
  };

  return (
    <div className="glass" style={{ padding: 24 }}>
      <h2>Join DirectTorrent.me</h2>
      {message && <p className="info-text">{message}</p>}
      {step === 'start' ? (
        <form onSubmit={handleStart} className="form-grid">
          <input
            placeholder="Username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
          <input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input
            placeholder="Password"
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          <button className="button-primary" type="submit">
            Send OTP
          </button>
        </form>
      ) : (
        <form onSubmit={handleVerify} className="form-grid">
          <input placeholder="Email" value={form.email} readOnly />
          <input
            placeholder="OTP code"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
          />
          <button className="button-primary" type="submit">
            Verify & Create account
          </button>
        </form>
      )}
      <p style={{ marginTop: 12 }}>
        Already have an account? <Link href="/login">Sign in</Link>
      </p>
    </div>
  );
}
