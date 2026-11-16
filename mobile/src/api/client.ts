import axios from 'axios';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { getAccessToken, getRefreshToken, setAccessToken, clearAllAuthTokens, getCourtToken } from '../utils/secureStore';

/**
 * Resolves the backend API base URL dynamically across:
 * 1. Explicit EXPO_PUBLIC_API_URL environment variable
 * 2. Expo Go / physical device over local Wi-Fi (via hostUri / debuggerHost)
 * 3. Android Emulator (10.0.2.2 connects to host Mac/PC)
 * 4. iOS Simulator / Web (127.0.0.1)
 */
const resolveApiBaseUrl = (): string => {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL.replace(/\/+$/, '');
  }

  // Check Expo Constants for dev bundler host
  const hostUri =
    Constants.expoConfig?.hostUri ||
    (Constants as any).expoGoConfig?.debuggerHost ||
    (Constants as any).manifest2?.extra?.expoClient?.hostUri;

  let devIp = '127.0.0.1';
  if (hostUri) {
    const rawHost = hostUri.split(':')[0];
    if (rawHost) {
      devIp = rawHost;
    }
  }

  // On Android, 127.0.0.1 or localhost points to the emulator/device loopback rather than the host computer.
  // 10.0.2.2 is the official loopback alias pointing to the host machine on the Android emulator.
  if (Platform.OS === 'android' && (devIp === '127.0.0.1' || devIp === 'localhost' || !hostUri)) {
    devIp = '10.0.2.2';
  }

  return `http://${devIp}:5001/api/v1`;
};

export const API_BASE_URL = resolveApiBaseUrl();

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
