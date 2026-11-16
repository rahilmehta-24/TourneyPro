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

interface AuthState {
  user: UserProfile | null;
  player: PlayerProfile | null;
  activeRole: UserRole;
  courtSession: CourtSession | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: UserProfile | null) => void;
  setPlayer: (player: PlayerProfile | null) => void;
  setActiveRole: (role: UserRole) => void;
  loginUser: (user: UserProfile, accessToken: string, refreshToken: string, player?: PlayerProfile) => Promise<void>;
  loginCourt: (courtSession: CourtSession, accessToken: string) => Promise<void>;
  restoreSession: () => Promise<boolean>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  player: null,
  activeRole: 'player',
  courtSession: null,
  isAuthenticated: false,
  isLoading: false,

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

  restoreSession: async () => {
    set({ isLoading: true });
    try {
      const accessToken = await getAccessToken();
      const courtToken = await getCourtToken();

      if (courtToken && !accessToken) {
        set({
          activeRole: 'umpire',
          isAuthenticated: true,
          isLoading: false,
        });
        return true;
      }

      if (!accessToken) {
        set({
          user: null,
          player: null,
          isAuthenticated: false,
          isLoading: false,
        });
        return false;
      }

      // Verify token with backend /users/me
      const res = await apiClient.get('/users/me');
      if (res.data?.success && res.data?.user) {
        const u = res.data.user;
        const p = res.data.player || null;
        const role: UserRole = u.role === 'superadmin' || u.role === 'admin' ? 'admin' : 'player';
        set({
          user: u,
          player: p,
          activeRole: role,
          isAuthenticated: true,
          isLoading: false,
        });
        return true;
      }

      // If user not returned
      await clearAllAuthTokens();
      set({
        user: null,
        player: null,
        isAuthenticated: false,
        isLoading: false,
      });
      return false;
    } catch (err) {
      await clearAllAuthTokens();
      set({
        user: null,
        player: null,
        isAuthenticated: false,
        isLoading: false,
      });
      return false;
    }
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


