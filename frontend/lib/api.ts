const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5000';

async function request(path: string, init?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data?.error || `API error ${res.status}`);
  }
  return data;
}

export const api = {
  me: () => request('/api/auth/me'),
  login: (email_or_username: string, password: string) =>
    request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email_or_username, password }) }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  registerStart: (payload: { username: string; email: string; password: string }) =>
    request('/api/auth/register/start', { method: 'POST', body: JSON.stringify(payload) }),
  registerVerify: (payload: { email: string; code: string }) =>
    request('/api/auth/register/verify', { method: 'POST', body: JSON.stringify(payload) }),
  passwordResetStart: (payload: { email: string }) =>
    request('/api/auth/password-reset/start', { method: 'POST', body: JSON.stringify(payload) }),
  passwordResetComplete: (payload: { email: string; code: string; new_password: string }) =>
    request('/api/auth/password-reset/complete', { method: 'POST', body: JSON.stringify(payload) }),
  createTorrent: (payload: Record<string, any>) =>
    request('/api/torrents', { method: 'POST', body: JSON.stringify(payload) }),
  listTorrents: (params?: URLSearchParams) => {
    const suffix = params ? `?${params.toString()}` : '';
    return request(`/api/torrents${suffix}`);
  },
  getTorrent: (id: number) => request(`/api/torrents/${id}`),
  cancelTorrent: (id: number) => request(`/api/torrents/${id}/cancel`, { method: 'POST' }),
};
