const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5000';

async function apiGet(path: string) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
  });

  if (!res.ok) {
    throw new Error(`API request failed: ${res.status}`);
  }

  return res.json();
}

async function apiPost(path: string, body: Record<string, any>) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(`API request failed: ${res.status}`);
  }

  return res.json();
}

export async function fetchSession() {
  return apiGet('/api/session');
}

export async function fetchTorrents() {
  return apiGet('/api/torrents');
}

export async function fetchTorrent(id: string) {
  return apiGet(`/api/torrents/${id}`);
}

export async function login(username: string, password: string) {
  return apiPost('/api/login', { username, password });
}
