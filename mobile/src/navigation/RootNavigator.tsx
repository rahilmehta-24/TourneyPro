import React from 'react';
import { useAuthStore } from '../state/authStore';
import LoginScreen from '../screens/auth/LoginScreen';
import MainTabNavigator from './MainTabNavigator';

export default function RootNavigator() {
  const { isAuthenticated, activeRole } = useAuthStore();

  // If not authenticated and not explicitly viewing as guest spectator, default to Login
  if (!isAuthenticated && activeRole !== 'spectator') {
    return <LoginScreen />;
  }

  // Once authenticated (or in spectator mode), render the dynamic role-based app
  return <MainTabNavigator />;
}

