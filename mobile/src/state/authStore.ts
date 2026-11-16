import { create } from 'zustand';
import { clearAllAuthTokens, setAccessToken, setRefreshToken, setCourtToken, getAccessToken, getRefreshToken, getCourtToken } from '../utils/secureStore';
import { apiClient } from '../api/client';

export type UserRole = 'player' | 'admin' | 'umpire' | 'spectator';

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  role: string;
  created_at?: string;
}

export interface PlayerProfile {
  id: number;
  name: string;
  registration_no?: string;
  gender?: string;
  age_category?: string;
  dob?: string;
  age?: number;
  contact_number?: string;
  nationality?: string;
  height?: string;
  weight?: string;
  blood_group?: string;
  current_status?: string;
  academy?: string;
  coach?: string;
  avatar_url?: string;
  total_points: number;
  matches_played: number;
  matches_won: number;
  matches_lost: number;
  win_rate: number;
}

export interface CourtSession {
  court: string;
  role: string;
  tournament: {
    id: number;
    name: string;
    slug: string;
  };
}

export interface SecurityCheckResult {
  status: 'PASS' | 'FAIL';
  description: string;
}

export interface SecurityVerificationReport {
  score: number;
  passed_checks: number;
  total_checks: number;
  checks: Record<string, SecurityCheckResult>;
}

interface AuthState {
  user: UserProfile | null;
  player: PlayerProfile | null;
  activeRole: UserRole;
  courtSession: CourtSession | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  securityReport: SecurityVerificationReport | null;
  securityVerified: boolean;
  setUser: (user: UserProfile | null) => void;
  setPlayer: (player: PlayerProfile | null) => void;
  setActiveRole: (role: UserRole) => void;
  loginUser: (user: UserProfile, accessToken: string, refreshToken: string, player?: PlayerProfile) => Promise<void>;
  loginCourt: (courtSession: CourtSession, accessToken: string) => Promise<void>;
  restoreSession: (maxRetries?: number) => Promise<boolean>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  player: null,
  activeRole: 'player',
  courtSession: null,
  isAuthenticated: false,
  isLoading: false,
  securityReport: null,
  securityVerified: false,

  setUser: (user) => set({
    user,
    isAuthenticated: !!user,
    activeRole: user?.role === 'superadmin' || user?.role === 'admin' ? 'admin' : 'player',
  }),

  setPlayer: (player) => set({ player }),

  setActiveRole: (activeRole) => set({ activeRole }),

  loginUser: async (user, accessToken, refreshToken, player) => {
    await setAccessToken(accessToken);
    await setRefreshToken(refreshToken);
    const role: UserRole = user.role === 'superadmin' || user.role === 'admin' ? 'admin' : 'player';
    set({
      user,
      player: player || null,
      activeRole: role,
      courtSession: null,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  loginCourt: async (courtSession, accessToken) => {
    await setCourtToken(accessToken);
    set({
      user: null,
      player: null,
      courtSession,
      activeRole: 'umpire',
      isAuthenticated: true,
      isLoading: false,
    });
  },

  restoreSession: async (maxRetries = 3) => {
    set({ isLoading: true });
    let attempt = 0;
    let lastError: any = null;

    while (attempt < maxRetries) {
      attempt++;
      try {
        const accessToken = await getAccessToken();
        const courtToken = await getCourtToken();

        if (courtToken && !accessToken) {
          set({
            activeRole: 'umpire',
            isAuthenticated: true,
            isLoading: false,
            securityVerified: true,
          });
          return true;
        }

        // Run full on-boot security verification check on the backend
        const headers: Record<string, string> = {};
        if (accessToken) {
          headers['Authorization'] = `Bearer ${accessToken}`;
        }

        const res = await apiClient.get('/security/app-verify', { headers });

        if (res.data?.success && res.data?.status === 'passed' && res.data?.score === 100) {
          const report: SecurityVerificationReport = {
            score: res.data.score,
            passed_checks: res.data.passed_checks,
            total_checks: res.data.total_checks,
            checks: res.data.checks,
          };

          if (res.data.user) {
            const u = res.data.user;
            const p = res.data.player || null;
            const role: UserRole = u.role === 'superadmin' || u.role === 'admin' ? 'admin' : 'player';
            set({
              user: u,
              player: p,
              activeRole: role,
              isAuthenticated: true,
              isLoading: false,
              securityReport: report,
              securityVerified: true,
            });
          } else {
            // Valid anonymous visitor baseline verified
            set({
              user: null,
              player: null,
              isAuthenticated: false,
              isLoading: false,
              securityReport: report,
              securityVerified: true,
            });
          }
          return true;
        }

        // Did not pass 100%, trigger retry
        lastError = new Error(`Security score ${res.data?.score}%. Verification incomplete.`);
      } catch (err: any) {
        lastError = err;

        // If 401 Unauthorized (e.g. access token expired), attempt token refresh before next retry
        if (err.response?.status === 401) {
          const refreshToken = await getRefreshToken();
          if (refreshToken) {
            try {
              const refreshRes = await apiClient.post('/auth/refresh', {}, {
                headers: { Authorization: `Bearer ${refreshToken}` },
              });
              if (refreshRes.data?.access_token) {
                await setAccessToken(refreshRes.data.access_token);
                continue; // Immediately retry verification with refreshed token
              }
            } catch {
              // Refresh token invalid, clear tokens
              await clearAllAuthTokens();
            }
          } else {
            await clearAllAuthTokens();
          }
        }
      }

      // If attempt failed and more retries remain, back off briefly (400ms, 800ms)
      if (attempt < maxRetries) {
        await new Promise((resolve) => setTimeout(resolve, attempt * 400));
      }
    }

    // If 3 retries exhausted:
    console.warn(`[Security] App security checks failed after ${maxRetries} attempts:`, lastError);
    await clearAllAuthTokens();
    set({
      user: null,
      player: null,
      isAuthenticated: false,
      isLoading: false,
      securityVerified: false,
    });
    return false;
  },

  logout: async () => {
    await clearAllAuthTokens();
    set({
      user: null,
      player: null,
      courtSession: null,
      activeRole: 'player',
      isAuthenticated: false,
      isLoading: false,
    });
  },
}));


