import axios from 'axios';
import { API_BASE_URL } from './constants';

let _accessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  _accessToken = token;
};

export const getAccessToken = () => _accessToken;

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  if (_accessToken) {
    config.headers.Authorization = `Bearer ${_accessToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    const url = original?.url || '';

    // Don't attempt refresh on auth endpoints (prevents infinite 401 loop)
    const isAuthEndpoint = url.includes('/v1/auth/');
    if (err.response?.status === 401 && !original._retry && !isAuthEndpoint) {
      original._retry = true;
      try {
        const { data } = await api.post('/v1/auth/refresh');
        setAccessToken(data.data.access_token);
        original.headers.Authorization = `Bearer ${data.data.access_token}`;
        return api(original);
      } catch {
        setAccessToken(null);
        // Signal auth expiry to AuthContext — it will clear state and
        // the AuthGuard will handle the redirect via client-side navigation.
        // Never use window.location.href here: it causes a full page reload
        // which re-triggers the refresh cycle and creates an infinite loop.
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('auth:session-expired'));
        }
      }
    }
    return Promise.reject(err);
  }
);
