import { create } from 'zustand';
import { clearAllAuthTokens, setAccessToken, setRefreshToken, setCourtToken } from '../utils/secureStore';

export type UserRole = 'player' | 'admin' | 'umpire' | 'spectator';

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  role: string;
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
  activeRole: UserRole;
  courtSession: CourtSession | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: UserProfile | null) => void;
  setActiveRole: (role: UserRole) => void;
  loginUser: (user: UserProfile, accessToken: string, refreshToken: string) => Promise<void>;
  loginCourt: (courtSession: CourtSession, accessToken: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  activeRole: 'player',
  courtSession: null,
  isAuthenticated: false,
  isLoading: false,

  setUser: (user) => set({
    user,
    isAuthenticated: !!user,
    activeRole: user?.role === 'superadmin' || user?.role === 'admin' ? 'admin' : 'player',
  }),

  setActiveRole: (activeRole) => set({ activeRole }),

  loginUser: async (user, accessToken, refreshToken) => {
    await setAccessToken(accessToken);
    await setRefreshToken(refreshToken);
    const role: UserRole = user.role === 'superadmin' || user.role === 'admin' ? 'admin' : 'player';
    set({
      user,
      activeRole: role,
      courtSession: null,
      isAuthenticated: true,
    });
  },

  loginCourt: async (courtSession, accessToken) => {
    await setCourtToken(accessToken);
    set({
      user: null,
      courtSession,
      activeRole: 'umpire',
      isAuthenticated: true,
    });
  },

  logout: async () => {
    await clearAllAuthTokens();
    set({
      user: null,
      courtSession: null,
      activeRole: 'spectator',
      isAuthenticated: false,
    });
  },
}));

