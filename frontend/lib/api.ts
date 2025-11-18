function normalizeApiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE;

  if (!raw) {
    // Avoid mixed-content failures when the frontend is served over HTTPS.
    if (typeof window !== 'undefined') {
      return `${window.location.protocol}//${window.location.host}`;
    }
    const deployHost = process.env.VERCEL_URL;
    if (deployHost) {
      return `https://${deployHost}`;
    }
    return 'http://localhost:5000';
  }

  if (/^https?:\/\//i.test(raw)) {
    if (typeof window !== 'undefined' && window.location.protocol === 'https:' && raw.startsWith('http://')) {
      return raw.replace('http://', 'https://');
    }
    return raw;
  }

  // Allow setting a bare host in NEXT_PUBLIC_API_BASE (e.g., "directtorrent-api.herokuapp.com").
  const protocol = typeof window !== 'undefined' ? window.location.protocol : 'https:';
  return `${protocol}//${raw}`;
}

const API_BASE = normalizeApiBase();

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

export async function fetchTorrent(id: number | string) {
  const data = await api.getTorrent(Number(id));
  return (data as any).job ?? data;
}
