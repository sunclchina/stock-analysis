/**
 * 操盘笔记 API 服务层
 * CRUD + 标签筛选 + 分页
 */

export interface TradingNote {
  id: number;
  title: string;
  content: string;
  stock_code: string;
  stock_name: string;
  tags: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface NoteListResponse {
  notes: TradingNote[];
  total: number;
}

export interface NoteCreatePayload {
  title: string;
  content?: string;
  stock_code?: string;
  stock_name?: string;
  tags?: string;
}

export interface NoteUpdatePayload {
  title?: string;
  content?: string;
  stock_code?: string;
  stock_name?: string;
  tags?: string;
  is_pinned?: boolean;
}

const BASE = '/api/v1/notes';

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `请求失败: ${res.status}`);
  }
  return res.json();
}

export async function listNotes(params?: {
  tag?: string;
  stock?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}): Promise<NoteListResponse> {
  const sp = new URLSearchParams();
  if (params?.tag) sp.set('tag', params.tag);
  if (params?.stock) sp.set('stock', params.stock);
  if (params?.keyword) sp.set('keyword', params.keyword);
  if (params?.page) sp.set('page', String(params.page));
  if (params?.page_size) sp.set('page_size', String(params.page_size));
  const qs = sp.toString();
  return apiFetch<NoteListResponse>(`${BASE}${qs ? '?' + qs : ''}`);
}

export async function getNote(id: number): Promise<TradingNote> {
  return apiFetch<TradingNote>(`${BASE}/${id}`);
}

export async function createNote(data: NoteCreatePayload): Promise<TradingNote> {
  return apiFetch<TradingNote>(BASE, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateNote(id: number, data: NoteUpdatePayload): Promise<TradingNote> {
  return apiFetch<TradingNote>(`${BASE}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteNote(id: number): Promise<{ message: string; id: number }> {
  return apiFetch<{ message: string; id: number }>(`${BASE}/${id}`, {
    method: 'DELETE',
  });
}
