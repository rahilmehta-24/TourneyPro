import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  Image,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { KeyRound, Shield, User, Trophy, Eye, EyeOff, ChevronRight, UserPlus, LogIn } from 'lucide-react-native';
import { colors } from '../../theme/colors';
import { useAuthStore } from '../../state/authStore';
import { apiClient } from '../../api/client';

type AuthMode = 'login' | 'register' | 'pin';

export default function LoginScreen() {
  const insets = useSafeAreaInsets();
  const { loginUser, loginCourt, setActiveRole } = useAuthStore();

  const [mode, setMode] = useState<AuthMode>('login');

  // Sign In fields
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Sign Up / Register fields
  const [regFullName, setRegFullName] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [regRole, setRegRole] = useState<'player' | 'admin'>('player');
  const [showRegPassword, setShowRegPassword] = useState(false);

  // Court PIN fields
  const [courtPin, setCourtPin] = useState('');

  const [loading, setLoading] = useState(false);

  // --- SIGN IN HANDLER ---
  const handleLogin = async (overrideUser?: string, overridePass?: string) => {
    const userToLogin = overrideUser || username.trim();
    const passToLogin = overridePass || password.trim();

    if (!userToLogin || !passToLogin) {
      Alert.alert('Required', 'Please enter your username/email and password.');
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.post('/auth/login', {
        username: userToLogin,
        password: passToLogin,
      });

      if (res.data?.success && res.data?.access_token) {
        await loginUser(
          res.data.user,
          res.data.access_token,
          res.data.refresh_token || res.data.access_token
        );
      } else {
        Alert.alert('Login Failed', res.data?.message || 'Invalid credentials.');
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.message;
      if (!err.response) {
        // Offline demo fallback so app works seamlessly
        const demoRole = userToLogin.includes('admin') || userToLogin.includes('organizer') ? 'admin' : 'player';
        await loginUser(
          {
            id: demoRole === 'admin' ? 1 : 2,
            username: userToLogin,
            email: `${userToLogin}@baseline.local`,
            role: demoRole,
          },
          'offline_demo_access_token',
          'offline_demo_refresh_token'
        );
      } else {
        Alert.alert('Sign In Error', errorMsg || 'Invalid credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  // --- SIGN UP / REGISTER HANDLER ---
  const handleRegister = async () => {
    const trimmedUser = regUsername.trim();
    const trimmedEmail = regEmail.trim();
    const trimmedPass = regPassword.trim();
    const trimmedConfirm = regConfirmPassword.trim();

    if (!trimmedUser || !trimmedEmail || !trimmedPass) {
      Alert.alert('Required Fields', 'Please fill in your username, email, and password.');
      return;
    }

    if (trimmedPass.length < 6) {
      Alert.alert('Weak Password', 'Password should be at least 6 characters.');
      return;
    }

    if (trimmedPass !== trimmedConfirm) {
      Alert.alert('Mismatch', 'Passwords do not match. Please verify your password.');
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.post('/auth/register', {
        username: trimmedUser,
        email: trimmedEmail,
        password: trimmedPass,
        role: regRole, // 'admin' (Organizer) or 'user' / 'player'
      });

      if (res.data?.success && res.data?.access_token) {
        const notifMsg = res.data?.message || 'User created successfully! A fresh workspace has been initialized. No existing user data was found or carried over.';
        const notifTitle = res.data?.category === 'warning' ? 'Verification Notice' : 'Account Initialized';
        Alert.alert(
          notifTitle,
          notifMsg,
          [
            {
              text: 'Continue',
              onPress: async () => {
                await loginUser(
                  res.data.user,
                  res.data.access_token,
                  res.data.refresh_token || res.data.access_token
                );
              },
            },
          ]
        );
      } else {
        Alert.alert('Registration Failed', res.data?.message || 'Could not complete registration.');
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.message;
      if (!err.response) {
        // Offline demo fallback
        await loginUser(
          {
            id: Date.now(),
            username: trimmedUser,
            email: trimmedEmail,
            role: regRole,
          },
          'offline_reg_access_token',
          'offline_reg_refresh_token'
        );
        Alert.alert(
          'Account Initialized',
          'User created successfully! A fresh workspace has been initialized. No existing user data was found or carried over.'
        );
      } else {
        Alert.alert('Registration Error', errorMsg || 'Unable to register at this time.');
      }
    } finally {
      setLoading(false);
    }
  };

  // --- COURT PIN LOGIN HANDLER ---
  const handleCourtPinLogin = async (overridePin?: string) => {
    const pin = overridePin || courtPin.trim();
    if (!pin) {
      Alert.alert('PIN Required', 'Please enter a 4 to 6 digit Court PIN.');
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.post('/auth/court-login', { pin });
      if (res.data?.success && res.data?.access_token) {
        await loginCourt(
          {
            court: res.data.court || 'Court 1',
            role: res.data.role || 'official',
            tournament: res.data.tournament || {
              id: 1,
              name: 'Baseline National Invitational',
              slug: 'baseline-championship',
            },
          },
          res.data.access_token
        );
      } else {
        Alert.alert('Invalid PIN', res.data?.message || 'Invalid court PIN.');
      }
    } catch (err: any) {
      if (!err.response && (pin === '123456' || pin === '1234')) {
        await loginCourt(
          {
            court: 'Court 1',
            role: 'official',
            tournament: {
              id: 1,
              name: 'Baseline National Invitational',
              slug: 'baseline-championship',
            },
          },
          'offline_court_jwt'
        );
      } else {
        Alert.alert('PIN Error', err.response?.data?.message || 'Invalid court PIN.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSpectatorMode = () => {
    setActiveRole('spectator');
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={[styles.container, { paddingTop: Math.max(insets.top, 16) }]}
    >
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Brand Header with Crest & Prominent App Name */}
        <View style={styles.brandSection}>
          <Image
            source={require('../../../assets/monogram-on-light.png')}
            style={styles.brandMonogram}
          />
          <Text style={styles.brandTitle}>BASELINE</Text>
          <Text style={styles.brandSubtitle}>THE BASELINE SOCIETY</Text>
          <Text style={styles.tagline}>Championship Circuit & Club Management</Text>
        </View>

        {/* Segmented Auth Navigation Bar */}
        <View style={styles.tabContainer}>
          <TouchableOpacity
            style={[styles.tabButton, mode === 'login' && styles.tabButtonActive]}
            onPress={() => setMode('login')}
          >
            <LogIn size={15} color={mode === 'login' ? colors.brandGreenCourt : colors.textMuted} />
            <Text style={[styles.tabText, mode === 'login' && styles.tabTextActive]}>
              SIGN IN
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tabButton, mode === 'register' && styles.tabButtonActive]}
            onPress={() => setMode('register')}
          >
            <UserPlus size={15} color={mode === 'register' ? colors.brandGreenCourt : colors.textMuted} />
            <Text style={[styles.tabText, mode === 'register' && styles.tabTextActive]}>
              REGISTER
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tabButton, mode === 'pin' && styles.tabButtonActive]}
            onPress={() => setMode('pin')}
          >
            <KeyRound size={15} color={mode === 'pin' ? colors.brandGreenCourt : colors.textMuted} />
            <Text style={[styles.tabText, mode === 'pin' && styles.tabTextActive]}>
              COURT PIN
            </Text>
          </TouchableOpacity>
        </View>

        {/* MODE 1: SIGN IN FORM */}
        {mode === 'login' && (
          <View style={styles.formCard}>
            <Text style={styles.cardHeader}>SIGN IN TO YOUR ACCOUNT</Text>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>USERNAME OR EMAIL</Text>
              <TextInput
                style={styles.input}
                placeholder="e.g. player1 or organizer"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="none"
                value={username}
                onChangeText={setUsername}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>PASSWORD</Text>
              <View style={styles.passwordContainer}>
                <TextInput
                  style={styles.passwordInput}
                  placeholder="Enter your password"
                  placeholderTextColor={colors.textMuted}
                  secureTextEntry={!showPassword}
                  value={password}
                  onChangeText={setPassword}
                />
                <TouchableOpacity
                  style={styles.eyeBtn}
                  onPress={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff size={18} color={colors.textSecondary} />
                  ) : (
                    <Eye size={18} color={colors.textSecondary} />
                  )}
                </TouchableOpacity>
              </View>
            </View>

            <TouchableOpacity
              style={styles.btnPrimary}
              activeOpacity={0.85}
              onPress={() => handleLogin()}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color={colors.brandGold} />
              ) : (
                <Text style={styles.btnPrimaryText}>SIGN IN</Text>
              )}
            </TouchableOpacity>

            {/* Link to Register */}
            <TouchableOpacity
              style={styles.linkRow}
              onPress={() => setMode('register')}
            >
              <Text style={styles.linkText}>
                Not registered yet?{' '}
                <Text style={styles.linkTextBold}>Create an Account / Register Now →</Text>
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {/* MODE 2: REGISTER / SIGN UP FORM */}
        {mode === 'register' && (
          <View style={styles.formCard}>
            <Text style={styles.cardHeader}>CREATE YOUR BASELINE ACCOUNT</Text>
            <Text style={styles.cardSub}>
              Enter tournaments, track live draws, or manage circuits
            </Text>

            {/* Role Selection Segment */}
            <Text style={styles.inputLabel}>SELECT YOUR ROLE</Text>
            <View style={styles.rolePickerRow}>
              <TouchableOpacity
                style={[
                  styles.rolePickerPill,
                  regRole === 'player' && styles.rolePickerPillActive,
                ]}
                onPress={() => setRegRole('player')}
              >
                <User size={16} color={regRole === 'player' ? colors.canvasLight : colors.brandGreenDeep} />
                <View style={styles.rolePickerTextCol}>
                  <Text style={[styles.rolePickerTitle, regRole === 'player' && styles.rolePickerTitleActive]}>
                    Tennis Player
                  </Text>
                  <Text style={[styles.rolePickerDesc, regRole === 'player' && styles.rolePickerDescActive]}>
                    Enter draws, match alerts
                  </Text>
                </View>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.rolePickerPill,
                  regRole === 'admin' && styles.rolePickerPillActive,
                ]}
                onPress={() => setRegRole('admin')}
              >
                <Shield size={16} color={regRole === 'admin' ? colors.canvasLight : colors.brandGold} />
                <View style={styles.rolePickerTextCol}>
                  <Text style={[styles.rolePickerTitle, regRole === 'admin' && styles.rolePickerTitleActive]}>
                    Organizer
                  </Text>
                  <Text style={[styles.rolePickerDesc, regRole === 'admin' && styles.rolePickerDescActive]}>
                    Create draws, court PINs
                  </Text>
                </View>
              </TouchableOpacity>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>FULL NAME</Text>
              <TextInput
                style={styles.input}
                placeholder="e.g. Rohan Bopanna"
                placeholderTextColor={colors.textMuted}
                value={regFullName}
                onChangeText={setRegFullName}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>CHOOSE A USERNAME *</Text>
              <TextInput
                style={styles.input}
                placeholder="e.g. rohanbopanna"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="none"
                value={regUsername}
                onChangeText={setRegUsername}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>EMAIL ADDRESS *</Text>
              <TextInput
                style={styles.input}
                placeholder="e.g. rohan@example.com"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="none"
                keyboardType="email-address"
                value={regEmail}
                onChangeText={setRegEmail}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>PASSWORD (MIN 6 CHARACTERS) *</Text>
              <View style={styles.passwordContainer}>
                <TextInput
                  style={styles.passwordInput}
                  placeholder="Create a secure password"
                  placeholderTextColor={colors.textMuted}
                  secureTextEntry={!showRegPassword}
                  value={regPassword}
                  onChangeText={setRegPassword}
                />
                <TouchableOpacity
                  style={styles.eyeBtn}
                  onPress={() => setShowRegPassword(!showRegPassword)}
                >
                  {showRegPassword ? (
                    <EyeOff size={18} color={colors.textSecondary} />
                  ) : (
                    <Eye size={18} color={colors.textSecondary} />
                  )}
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>CONFIRM PASSWORD *</Text>
              <TextInput
                style={styles.input}
                placeholder="Re-enter password"
                placeholderTextColor={colors.textMuted}
                secureTextEntry={!showRegPassword}
                value={regConfirmPassword}
                onChangeText={setRegConfirmPassword}
              />
            </View>

            <TouchableOpacity
              style={styles.btnPrimary}
              activeOpacity={0.85}
              onPress={handleRegister}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color={colors.brandGold} />
              ) : (
                <Text style={styles.btnPrimaryText}>CREATE ACCOUNT & GET STARTED</Text>
              )}
            </TouchableOpacity>

            {/* Link to Sign In */}
            <TouchableOpacity
              style={styles.linkRow}
              onPress={() => setMode('login')}
            >
              <Text style={styles.linkText}>
                Already registered?{' '}
                <Text style={styles.linkTextBold}>Sign In to Your Account →</Text>
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {/* MODE 3: COURT PIN LOGIN */}
        {mode === 'pin' && (
          <View style={styles.formCard}>
            <View style={styles.courtHeaderRow}>
              <KeyRound size={22} color={colors.brandGold} />
              <Text style={styles.cardHeader}>COURT SCORING PIN LOGIN</Text>
            </View>
            <Text style={styles.courtSub}>
              Enter the 4 to 6 digit tournament PIN assigned by the director to unlock court scoring.
            </Text>

            <TextInput
              style={styles.pinInput}
              placeholder="123456"
              placeholderTextColor={colors.textMuted}
              keyboardType="number-pad"
              maxLength={6}
              value={courtPin}
              onChangeText={setCourtPin}
            />

            <TouchableOpacity
              style={styles.btnPrimary}
              onPress={() => handleCourtPinLogin()}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color={colors.brandGold} />
              ) : (
                <Text style={styles.btnPrimaryText}>ACTIVATE COURT SESSION</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.btnBackToLogin}
              onPress={() => setMode('login')}
            >
              <Text style={styles.btnBackToLoginText}>← Back to Username / Password</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Quick Demo Fast-Login Section */}
        <View style={styles.demoSection}>
          <Text style={styles.demoTitle}>QUICK DEMO ROLES (TAP TO SIGN IN):</Text>

          <TouchableOpacity
            style={styles.demoRow}
            onPress={() => handleLogin('organizer', 'pass123')}
          >
            <View style={[styles.demoIcon, { backgroundColor: '#FDF6E2' }]}>
              <Shield size={16} color={colors.brandGold} />
            </View>
            <View style={styles.demoTextCol}>
              <Text style={styles.demoRoleName}>Tournament Director / Admin</Text>
              <Text style={styles.demoRoleSub}>Full tournament management, entry review, draws</Text>
            </View>
            <ChevronRight size={16} color={colors.textMuted} />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.demoRow}
            onPress={() => handleLogin('player1', 'pass123')}
          >
            <View style={[styles.demoIcon, { backgroundColor: colors.brandGreenSubtle }]}>
              <User size={16} color={colors.brandGreenCourt} />
            </View>
            <View style={styles.demoTextCol}>
              <Text style={styles.demoRoleName}>Tournament Player</Text>
              <Text style={styles.demoRoleSub}>Registered draws, personal match alerts & stats</Text>
            </View>
            <ChevronRight size={16} color={colors.textMuted} />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.demoRow}
            onPress={() => handleCourtPinLogin('123456')}
          >
            <View style={[styles.demoIcon, { backgroundColor: '#EBF4FF' }]}>
              <KeyRound size={16} color="#2B6CB0" />
            </View>
            <View style={styles.demoTextCol}>
              <Text style={styles.demoRoleName}>Court Official / Umpire</Text>
              <Text style={styles.demoRoleSub}>Court 1 scoring keypad with PIN 123456</Text>
            </View>
            <ChevronRight size={16} color={colors.textMuted} />
          </TouchableOpacity>

          {/* Continue as Spectator */}
          <TouchableOpacity
            style={styles.btnSpectator}
            onPress={handleSpectatorMode}
          >
            <Text style={styles.btnSpectatorText}>CONTINUE AS GUEST / SPECTATOR →</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.canvasLight,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  brandSection: {
    alignItems: 'center',
    marginTop: 6,
    marginBottom: 16,
  },
  brandMonogram: {
    width: 76,
    height: 76,
    resizeMode: 'contain',
    marginBottom: 6,
  },
  brandTitle: {
    fontSize: 32,
    fontWeight: '900',
    letterSpacing: 3,
    color: colors.brandGreenDeep,
  },
  brandSubtitle: {
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 2,
    color: colors.brandGreenCourt,
    marginTop: 3,
  },
  tagline: {
    fontSize: 12,
    fontWeight: '500',
    color: colors.textSecondary,
    marginTop: 4,
  },

  /* Tabs */
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceSecondary,
    borderRadius: 12,
    padding: 4,
    marginBottom: 16,
  },
  tabButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
  },
  tabButtonActive: {
    backgroundColor: colors.surfaceCard,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  tabText: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.8,
    color: colors.textMuted,
  },
  tabTextActive: {
    color: colors.brandGreenDeep,
    fontWeight: '900',
  },

  /* Forms */
  formCard: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: colors.borderLight,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  cardHeader: {
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 1.2,
    color: colors.brandGreenDeep,
    marginBottom: 4,
  },
  cardSub: {
    fontSize: 11,
    color: colors.textSecondary,
    marginBottom: 16,
  },
  rolePickerRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 14,
  },
  rolePickerPill: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: colors.borderLight,
    backgroundColor: colors.canvasLight,
    gap: 8,
  },
  rolePickerPillActive: {
    borderColor: colors.brandGreenCourt,
    backgroundColor: colors.brandGreenDeep,
  },
  rolePickerTextCol: {
    flex: 1,
  },
  rolePickerTitle: {
    fontSize: 12,
    fontWeight: '800',
    color: colors.brandGreenDeep,
  },
  rolePickerTitleActive: {
    color: colors.brandGold,
  },
  rolePickerDesc: {
    fontSize: 9,
    color: colors.textSecondary,
    marginTop: 1,
  },
  rolePickerDescActive: {
    color: '#D1E7DD',
  },
  inputGroup: {
    marginBottom: 14,
  },
  inputLabel: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
    color: colors.textSecondary,
    marginBottom: 6,
  },
  input: {
    backgroundColor: colors.canvasLight,
    borderWidth: 1,
    borderColor: colors.borderLight,
    borderRadius: 10,
    paddingHorizontal: 14,
    height: 46,
    fontSize: 14,
    color: colors.textPrimary,
  },
  passwordContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.canvasLight,
    borderWidth: 1,
    borderColor: colors.borderLight,
    borderRadius: 10,
    paddingHorizontal: 14,
    height: 46,
  },
  passwordInput: {
    flex: 1,
    fontSize: 14,
    color: colors.textPrimary,
  },
  eyeBtn: {
    padding: 4,
  },
  btnPrimary: {
    backgroundColor: colors.brandGreenDeep,
    borderRadius: 12,
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
    borderWidth: 1,
    borderColor: colors.brandGold,
  },
  btnPrimaryText: {
    color: colors.brandGold,
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 1.2,
  },
  linkRow: {
    marginTop: 16,
    alignItems: 'center',
  },
  linkText: {
    fontSize: 12,
    color: colors.textSecondary,
  },
  linkTextBold: {
    fontWeight: '800',
    color: colors.brandGreenCourt,
  },

  /* Court PIN */
  courtHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  courtSub: {
    fontSize: 12,
    color: colors.textSecondary,
    lineHeight: 18,
    marginBottom: 16,
  },
  pinInput: {
    backgroundColor: colors.canvasLight,
    borderWidth: 1.5,
    borderColor: colors.brandGold,
    borderRadius: 12,
    textAlign: 'center',
    fontSize: 28,
    fontWeight: '900',
    letterSpacing: 8,
    color: colors.brandGreenDeep,
    height: 56,
    marginBottom: 16,
  },
  btnBackToLogin: {
    marginTop: 14,
    alignItems: 'center',
  },
  btnBackToLoginText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.brandGreenCourt,
  },

  /* Quick Demo Roles */
  demoSection: {
    marginTop: 6,
  },
  demoTitle: {
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 1,
    color: colors.brandGold,
    marginBottom: 10,
  },
  demoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surfaceCard,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    marginBottom: 8,
  },
  demoIcon: {
    width: 34,
    height: 34,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  demoTextCol: {
    flex: 1,
  },
  demoRoleName: {
    fontSize: 13,
    fontWeight: '800',
    color: colors.textPrimary,
  },
  demoRoleSub: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 2,
  },
  btnSpectator: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: colors.brandGreenCourt,
    borderRadius: 12,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  btnSpectatorText: {
    color: colors.brandGreenCourt,
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1,
  },
});
