import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const ACCESS_TOKEN_KEY = 'baseline_access_token';
const REFRESH_TOKEN_KEY = 'baseline_refresh_token';
const COURT_PIN_TOKEN_KEY = 'baseline_court_token';

// In-memory fallback if secure store fails or on unsupported platform
const memoryStore = new Map<string, string>();

export async function setItem(key: string, value: string): Promise<void> {
  try {
    if (Platform.OS === 'web') {
      memoryStore.set(key, value);
      return;
    }
    await SecureStore.setItemAsync(key, value);
  } catch (err) {
    memoryStore.set(key, value);
  }
}

export async function getItem(key: string): Promise<string | null> {
  try {
    if (Platform.OS === 'web') {
      return memoryStore.get(key) || null;
    }
    const val = await SecureStore.getItemAsync(key);
    return val !== null ? val : memoryStore.get(key) || null;
  } catch (err) {
    return memoryStore.get(key) || null;
  }
}

export async function removeItem(key: string): Promise<void> {
  try {
    if (Platform.OS !== 'web') {
      await SecureStore.deleteItemAsync(key);
    }
    memoryStore.delete(key);
  } catch (err) {
    memoryStore.delete(key);
  }
}

export const setAccessToken = (token: string) => setItem(ACCESS_TOKEN_KEY, token);
export const getAccessToken = () => getItem(ACCESS_TOKEN_KEY);
export const removeAccessToken = () => removeItem(ACCESS_TOKEN_KEY);

export const setRefreshToken = (token: string) => setItem(REFRESH_TOKEN_KEY, token);
export const getRefreshToken = () => getItem(REFRESH_TOKEN_KEY);
export const removeRefreshToken = () => removeItem(REFRESH_TOKEN_KEY);

export const setCourtToken = (token: string) => setItem(COURT_PIN_TOKEN_KEY, token);
export const getCourtToken = () => getItem(COURT_PIN_TOKEN_KEY);
export const removeCourtToken = () => removeItem(COURT_PIN_TOKEN_KEY);

export async function clearAllAuthTokens(): Promise<void> {
  await Promise.all([
    removeAccessToken(),
    removeRefreshToken(),
    removeCourtToken(),
  ]);
}

