// Small client for the recommender API. All calls go through here.
// In a production build the API is served from the same origin as the page.
const FALLBACK = import.meta.env.DEV ? 'http://localhost:5000' : '';
const BASE = (import.meta.env.VITE_API_URL ?? FALLBACK).replace(/\/+$/, '');

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request(path, { method = 'GET', body, signal, timeout } = {}) {
  // Optional timeout, combined with the caller's own abort signal.
  const controller = new AbortController();
  const onAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener('abort', onAbort);
  }
  const timer = timeout ? setTimeout(() => controller.abort(), timeout) : null;

  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    if (signal && signal.aborted) throw err;
    throw new ApiError('Could not reach the server. Check your connection and try again.', 0);
  } finally {
    if (timer) clearTimeout(timer);
    if (signal) signal.removeEventListener('abort', onAbort);
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const fallback = res.status === 404 ? 'Not found.' : 'The server ran into a problem. Please try again.';
    throw new ApiError((data && data.error) || fallback, res.status);
  }
  return data;
}

export const recommend = (params, opts) =>
  request('/api/recommend', { method: 'POST', body: params, ...opts });

export const search = (params, opts) =>
  request('/api/search', { method: 'POST', body: params, ...opts });

export const getRecipe = (id, opts) => request(`/api/recipe/${encodeURIComponent(id)}`, opts);

export const getSimilar = (id, opts) =>
  request(`/api/recipe/${encodeURIComponent(id)}/similar`, opts);

export const getMeta = (opts) => request('/api/meta', opts);

export const checkHealth = (opts) => request('/api/health', { timeout: 6000, ...opts });
