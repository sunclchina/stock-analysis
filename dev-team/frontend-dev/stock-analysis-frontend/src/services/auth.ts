/**
 * 用户认证工具函数。
 */

export function getToken(): string | null {
  return localStorage.getItem('token');
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

export function getCurrentUser(): any {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null');
  } catch {
    return null;
  }
}

export function isAdmin(): boolean {
  const user = getCurrentUser();
  return user?.role === 'admin';
}

export function logout(): void {
  localStorage.removeItem('token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  window.location.href = '/login';
}

/** 带 Auth 的 fetch */
export async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = 'Bearer ' + token;
  }
  const r = await fetch(url, { ...options, headers });
  if (r.status === 401) {
    logout();
  }
  return r;
}
