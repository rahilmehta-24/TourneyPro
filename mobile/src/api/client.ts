import axios from 'axios';
import Constants from 'expo-constants';
import { getAccessToken, getRefreshToken, setAccessToken, clearAllAuthTokens, getCourtToken } from '../utils/secureStore';

// Auto-detect Mac/dev server IP when streaming over Wi-Fi to physical Expo Go
const hostUri = Constants.expoConfig?.hostUri;
const devIp = hostUri ? hostUri.split(':')[0] : '127.0.0.1';

export const API_BASE_URL = `http://${devIp}:5001/api/v1`;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Request Interceptor: Attach JWT or Court PIN token
apiClient.interceptors.request.use(async (config) => {
  const token = (await getAccessToken()) || (await getCourtToken());
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

// Response Interceptor: Handle Refresh Rotation & Concurrency Conflicts
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Concurrency conflict detection (HTTP 409)
    if (error.response?.status === 409) {
      // Return error for screen level toast/alert
      return Promise.reject(error);
    }

    // Unauthorized (HTTP 401) -> Attempt refresh token rotation
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = await getRefreshToken();
        if (refreshToken) {
          const res = await axios.post(`${API_BASE_URL}/auth/refresh`, {}, {
            headers: { Authorization: `Bearer ${refreshToken}` },
          });

          if (res.data?.access_token) {
            await setAccessToken(res.data.access_token);
            originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`;
            return apiClient(originalRequest);
          }
        }
      } catch (refreshErr) {
        await clearAllAuthTokens();
      }
    }

    return Promise.reject(error);
  }
);

