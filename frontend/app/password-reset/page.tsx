'use client';

import { FormEvent, useState } from 'react';
import { api } from '../../lib/api';

export default function PasswordResetPage() {
  const [step, setStep] = useState<'start' | 'complete'>('start');
  const [form, setForm] = useState({ email: '', code: '', new_password: '' });
  const [message, setMessage] = useState<string | null>(null);

  const start = async (e: FormEvent) => {
    e.preventDefault();
    await api.passwordResetStart({ email: form.email });
    setMessage('Check your email for the OTP.');
    setStep('complete');
  };

  const complete = async (e: FormEvent) => {
    e.preventDefault();
    await api.passwordResetComplete(form);
    setMessage('Password updated. You can sign in again.');
  };

  return (
    <div className="glass" style={{ padding: 24 }}>
      <h2>Password reset</h2>
      {message && <p className="info-text">{message}</p>}
      {step === 'start' ? (
        <form onSubmit={start} className="form-grid">
          <input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <button className="button-primary" type="submit">
            Send reset OTP
          </button>
        </form>
      ) : (
        <form onSubmit={complete} className="form-grid">
          <input placeholder="Email" value={form.email} readOnly />
          <input placeholder="Code" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          <input
            placeholder="New password"
            type="password"
            value={form.new_password}
            onChange={(e) => setForm({ ...form, new_password: e.target.value })}
          />
          <button className="button-primary" type="submit">
            Update password
          </button>
        </form>
      )}
    </div>
  );
}
