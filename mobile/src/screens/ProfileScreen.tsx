import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
  Modal,
  TextInput,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  RefreshControl,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { User, Bell, Shield, Trash2, LogOut, Award, ChevronRight, UserPlus, X, Trophy, CheckSquare, Square } from 'lucide-react-native';
import { colors } from '../theme/colors';
import { useAuthStore } from '../state/authStore';
import { apiClient } from '../api/client';

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();
  const { user, player, setPlayer, logout, activeRole, setActiveRole } = useAuthStore();

  const [refreshing, setRefreshing] = useState(false);
  const [notifyMatchCall, setNotifyMatchCall] = useState(true);
  const [notifyDraws, setNotifyDraws] = useState(true);
  const [notifyResults, setNotifyResults] = useState(true);

  // Admin User Provisioning state
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [adminUsername, setAdminUsername] = useState('');
  const [adminEmail, setAdminEmail] = useState('');
  const [adminFullName, setAdminFullName] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [adminRole, setAdminRole] = useState<'player' | 'umpire' | 'admin'>('player');
  const [adminSubmitting, setAdminSubmitting] = useState(false);

  // Tournament Organizer Activation state
  const [showOrganizerModal, setShowOrganizerModal] = useState(false);
  const [orgClubName, setOrgClubName] = useState('');
  const [orgPhone, setOrgPhone] = useState('');
  const [orgAgreed, setOrgAgreed] = useState(false);
  const [orgSubmitting, setOrgSubmitting] = useState(false);

  const fetchProfileAndPrefs = async () => {
    try {
      const [userRes, prefsRes] = await Promise.allSettled([
        apiClient.get('/users/me'),
        apiClient.get('/users/notification-preferences'),
      ]);

      if (userRes.status === 'fulfilled' && userRes.value.data?.success) {
        if (userRes.value.data.player) {
          setPlayer(userRes.value.data.player);
        }
      }

      if (prefsRes.status === 'fulfilled' && prefsRes.value.data) {
        const p = prefsRes.value.data;
        if (typeof p.match_call !== 'undefined') setNotifyMatchCall(!!p.match_call);
        if (typeof p.draws_published !== 'undefined') setNotifyDraws(!!p.draws_published);
        if (typeof p.final_results !== 'undefined') setNotifyResults(!!p.final_results);
      }
    } catch {
      // Ignore network errors on passive load
    }
  };

  useEffect(() => {
    fetchProfileAndPrefs();
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchProfileAndPrefs();
    setRefreshing(false);
  };

  const updatePreference = async (key: 'match_call' | 'draws_published' | 'final_results', val: boolean) => {
    try {
      await apiClient.put('/users/notification-preferences', {
        [key]: val,
      });
    } catch {
      Alert.alert('Notice', 'Unable to save notification preference.');
    }
  };

  const handleToggleMatchCall = (val: boolean) => {
    setNotifyMatchCall(val);
    updatePreference('match_call', val);
  };

  const handleToggleDraws = (val: boolean) => {
    setNotifyDraws(val);
    updatePreference('draws_published', val);
  };

  const handleToggleResults = (val: boolean) => {
    setNotifyResults(val);
    updatePreference('final_results', val);
  };

  const handleAdminCreateUser = async () => {
    if (!adminUsername.trim() || !adminEmail.trim() || !adminPassword.trim()) {
      Alert.alert('Required Fields', 'Username, email, and password are required.');
      return;
    }
    setAdminSubmitting(true);
    try {
      const res = await apiClient.post('/admin/users', {
        username: adminUsername.trim(),
        email: adminEmail.trim(),
        full_name: adminFullName.trim(),
        password: adminPassword.trim(),
        role: adminRole,
      });

      if (res.data?.success) {
        setShowAdminModal(false);
        setAdminUsername('');
        setAdminEmail('');
        setAdminFullName('');
        setAdminPassword('');
        const title = res.data.category === 'warning' ? 'Verification Notice' : 'User Provisioned';
        Alert.alert(title, res.data.message);
      } else {
        Alert.alert('Provisioning Failed', res.data?.message || 'Failed to create user.');
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.message || err.message || 'Failed to create user.';
      Alert.alert('Error', errorMsg);
    } finally {
      setAdminSubmitting(false);
    }
  };

  const handleActivateOrganizer = async () => {
    const trimmedOrg = orgClubName.trim();
    if (!trimmedOrg || trimmedOrg.length < 3) {
      Alert.alert('Validation Error', 'Organization / club name must be at least 3 characters.');
      return;
    }
    if (!orgAgreed) {
      Alert.alert('Agreement Required', 'You must agree to the Tournament Organizer Fair Play & Security terms.');
      return;
    }
    setOrgSubmitting(true);
    try {
      const res = await apiClient.post('/organizer/activate', {
        organization_name: trimmedOrg,
        contact_phone: orgPhone.trim(),
        agreed_terms: true,
      });
      if (res.data?.success) {
        if (res.data.user) {
          useAuthStore.getState().setUser(res.data.user);
          setActiveRole('admin');
        }
        setShowOrganizerModal(false);
        Alert.alert('Organizer Activated!', res.data.message || 'You are now authorized to host tournaments.');
        await fetchProfileAndPrefs();
      } else {
        Alert.alert('Activation Failed', res.data?.message || 'Could not complete organizer activation.');
      }
    } catch (err: any) {
      Alert.alert('Error', err.response?.data?.message || 'Failed to activate organizer permissions.');
    } finally {
      setOrgSubmitting(false);
    }
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      'Delete Baseline Account',
      'Are you sure you want to delete your account? All registered push tokens, personal profiles, and preferences will be permanently scrubbed per Google Play and Apple policy.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete Account',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiClient.post('/users/delete_account');
            } catch {
              // Proceed with client logout even if backend failed or already removed
            }
            await logout();
            Alert.alert('Account Deleted', 'Your account and personal data have been scrubbed successfully.');
          },
        },
      ]
    );
  };

  const displayName = player?.name || user?.username || 'Player';
  const displayId = player?.registration_no || (user ? `BS-UID-${user.id}` : 'PENDING');
  const initials = displayName.slice(0, 2).toUpperCase();
  const playedCount = player?.matches_played ?? 0;
  const wonCount = player?.matches_won ?? 0;
  const lostCount = player?.matches_lost ?? 0;
  const winRate = player?.win_rate ?? (playedCount > 0 ? Math.round((wonCount / playedCount) * 100) : 0);

  return (
    <View style={[styles.container, { paddingTop: Math.max(insets.top, 16) }]}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>PLAYER PROFILE</Text>
          <Text style={styles.subtitle}>BASELINE SOCIETY ID #{displayId}</Text>
        </View>
        <TouchableOpacity style={styles.badgeRank}>
          <Text style={styles.badgeRankText}>
            {player?.total_points ? `${player.total_points} PTS` : 'ACTIVE'}
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.brandGreenCourt} />}
      >
        {/* Player Profile Card */}
        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{initials}</Text>
          </View>
          <View style={styles.profileDetails}>
            <Text style={styles.playerName}>{displayName}</Text>
            <Text style={styles.playerRole}>
              {player?.age_category || 'Open Category'} • {player?.gender || 'Member'}
            </Text>
            <Text style={styles.playerClub}>{player?.academy || 'The Baseline Society Registry'}</Text>
          </View>
        </View>

        {/* Career Stats Grid */}
        <View style={styles.statsGrid}>
          <View style={styles.statBox}>
            <Text style={styles.statNum}>{playedCount}</Text>
            <Text style={styles.statLabel}>PLAYED</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={[styles.statNum, { color: colors.brandGreenCourt }]}>{wonCount}</Text>
            <Text style={styles.statLabel}>WON</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={[styles.statNum, { color: colors.brandClay }]}>{lostCount}</Text>
            <Text style={styles.statLabel}>LOST</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={[styles.statNum, { color: colors.brandGold }]}>{winRate}%</Text>
            <Text style={styles.statLabel}>WIN RATE</Text>
          </View>
        </View>

        {/* Notification Preferences */}
        <Text style={styles.sectionTitle}>PUSH NOTIFICATIONS & ALERTS</Text>
        <View style={styles.settingsGroup}>
          <View style={styles.settingRow}>
            <View style={styles.settingTextCol}>
              <Text style={styles.settingLabel}>Match Called to Court</Text>
              <Text style={styles.settingSub}>Immediate push alert when court is assigned</Text>
            </View>
            <Switch
              value={notifyMatchCall}
              onValueChange={handleToggleMatchCall}
              trackColor={{ false: colors.surfaceSecondary, true: colors.brandGreenCourt }}
            />
          </View>

          <View style={styles.settingRow}>
            <View style={styles.settingTextCol}>
              <Text style={styles.settingLabel}>Draws Published</Text>
              <Text style={styles.settingSub}>When schedule and brackets go live</Text>
            </View>
            <Switch
              value={notifyDraws}
              onValueChange={handleToggleDraws}
              trackColor={{ false: colors.surfaceSecondary, true: colors.brandGreenCourt }}
            />
          </View>

          <View style={styles.settingRow}>
            <View style={styles.settingTextCol}>
              <Text style={styles.settingLabel}>Final Score Results</Text>
              <Text style={styles.settingSub}>Daily match conclusion digests</Text>
            </View>
            <Switch
              value={notifyResults}
              onValueChange={handleToggleResults}
              trackColor={{ false: colors.surfaceSecondary, true: colors.brandGreenCourt }}
            />
          </View>
        </View>

        {/* Tournament Hosting */}
        <Text style={styles.sectionTitle}>TOURNAMENT HOSTING</Text>
        <View style={styles.settingsGroup}>
          {user?.role === 'user' ? (
            <TouchableOpacity
              style={styles.actionRow}
              onPress={() => {
                setOrgClubName(player?.academy || '');
                setOrgPhone(player?.contact_number || '');
                setOrgAgreed(false);
                setShowOrganizerModal(true);
              }}
            >
              <Trophy size={18} color={colors.brandGold} />
              <View style={{ flex: 1, marginLeft: 10 }}>
                <Text style={[styles.actionLabel, { marginLeft: 0, color: colors.brandGreenDeep }]}>
                  Become a Tournament Host
                </Text>
                <Text style={styles.settingSub}>
                  Activate organizer permissions to host tournaments & manage draws
                </Text>
              </View>
              <ChevronRight size={16} color={colors.textMuted} style={styles.chevron} />
            </TouchableOpacity>
          ) : (
            <View style={styles.actionRow}>
              <Trophy size={18} color={colors.brandGreenCourt} />
              <View style={{ flex: 1, marginLeft: 10 }}>
                <Text style={[styles.actionLabel, { marginLeft: 0 }]}>Active Tournament Host</Text>
                <Text style={styles.settingSub}>
                  Authorized organizer • {user?.role.toUpperCase()}
                </Text>
              </View>
            </View>
          )}
        </View>

        {/* Administrator Actions */}
        {(activeRole === 'admin' || user?.role === 'admin' || user?.role === 'superadmin') && (
          <>
            <Text style={styles.sectionTitle}>ADMINISTRATOR ACTIONS</Text>
            <View style={styles.settingsGroup}>
              <TouchableOpacity
                style={styles.actionRow}
                onPress={() => setShowAdminModal(true)}
              >
                <UserPlus size={18} color={colors.brandGreenCourt} />
                <View style={{ flex: 1, marginLeft: 10 }}>
                  <Text style={styles.actionLabel}>Provision User Account</Text>
                  <Text style={styles.settingSub}>Create user with clean workspace verification</Text>
                </View>
                <ChevronRight size={16} color={colors.textMuted} style={styles.chevron} />
              </TouchableOpacity>
            </View>
          </>
        )}

        {/* Account Actions */}
        <Text style={styles.sectionTitle}>ACCOUNT & PRIVACY</Text>
        <View style={styles.settingsGroup}>
          <TouchableOpacity style={styles.actionRow} onPress={() => logout()}>
            <LogOut size={18} color={colors.textSecondary} />
            <Text style={styles.actionLabel}>Log Out of Baseline</Text>
            <ChevronRight size={16} color={colors.textMuted} style={styles.chevron} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionRow} onPress={handleDeleteAccount}>
            <Trash2 size={18} color={colors.brandClay} />
            <Text style={[styles.actionLabel, { color: colors.brandClay }]}>
              Delete Account & Scrub PII
            </Text>
            <ChevronRight size={16} color={colors.textMuted} style={styles.chevron} />
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* Admin User Provisioning Modal */}
      <Modal
        visible={showAdminModal}
        animationType="slide"
        transparent
        onRequestClose={() => setShowAdminModal(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.modalOverlay}
        >
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <View>
                <Text style={styles.modalTitle}>PROVISION USER</Text>
                <Text style={styles.modalSubtitle}>DATA ISOLATION & VERIFICATION</Text>
              </View>
              <TouchableOpacity onPress={() => setShowAdminModal(false)} style={styles.closeBtn}>
                <X size={20} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false} style={{ maxHeight: 380 }}>
              <Text style={styles.fieldLabel}>FULL NAME</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="e.g. Full Name"
                placeholderTextColor={colors.textMuted}
                value={adminFullName}
                onChangeText={setAdminFullName}
              />

              <Text style={styles.fieldLabel}>USERNAME *</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="e.g. calcaraz"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="none"
                value={adminUsername}
                onChangeText={setAdminUsername}
              />

              <Text style={styles.fieldLabel}>EMAIL *</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="e.g. carlos@baseline.local"
                placeholderTextColor={colors.textMuted}
                keyboardType="email-address"
                autoCapitalize="none"
                value={adminEmail}
                onChangeText={setAdminEmail}
              />

              <Text style={styles.fieldLabel}>PASSWORD *</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="Min. 6 characters"
                placeholderTextColor={colors.textMuted}
                secureTextEntry
                value={adminPassword}
                onChangeText={setAdminPassword}
              />

              <Text style={styles.fieldLabel}>ASSIGNED ROLE</Text>
              <View style={styles.rolePicker}>
                {(['player', 'umpire', 'admin'] as const).map((r) => (
                  <TouchableOpacity
                    key={r}
                    style={[
                      styles.roleChip,
                      adminRole === r && styles.roleChipActive,
                    ]}
                    onPress={() => setAdminRole(r)}
                  >
                    <Text
                      style={[
                        styles.roleChipText,
                        adminRole === r && styles.roleChipTextActive,
                      ]}
                    >
                      {r.toUpperCase()}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>

            <TouchableOpacity
              style={[styles.modalSubmitBtn, adminSubmitting && { opacity: 0.7 }]}
              onPress={handleAdminCreateUser}
              disabled={adminSubmitting}
            >
              {adminSubmitting ? (
                <ActivityIndicator color={colors.surfaceCard} size="small" />
              ) : (
                <Text style={styles.modalSubmitText}>CREATE & VERIFY WORKSPACE</Text>
              )}
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Tournament Organizer Self-Activation Modal */}
      <Modal
        visible={showOrganizerModal}
        animationType="slide"
        transparent
        onRequestClose={() => setShowOrganizerModal(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.modalOverlay}
        >
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <View>
                <Text style={styles.modalTitle}>BECOME A HOST</Text>
                <Text style={styles.modalSubtitle}>BASELINE SOCIETY HOST NETWORK</Text>
              </View>
              <TouchableOpacity onPress={() => setShowOrganizerModal(false)} style={styles.closeBtn}>
                <X size={20} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false} style={{ maxHeight: 420 }}>
              <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 12, lineHeight: 18 }}>
                As an authorized tournament organizer, you can create official tournaments, manage registrations, publish draws, and schedule matches.
              </Text>

              <Text style={styles.fieldLabel}>CLUB / ACADEMY / ORGANIZATION NAME *</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="e.g. Metro Tennis Club or Independent Host"
                placeholderTextColor={colors.textMuted}
                value={orgClubName}
                onChangeText={setOrgClubName}
              />

              <Text style={styles.fieldLabel}>CONTACT PHONE NUMBER (OPTIONAL)</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="e.g. +91 98765 43210"
                placeholderTextColor={colors.textMuted}
                value={orgPhone}
                onChangeText={setOrgPhone}
                keyboardType="phone-pad"
              />

              <TouchableOpacity
                style={{ flexDirection: 'row', alignItems: 'flex-start', marginTop: 14, backgroundColor: colors.canvasLight, padding: 10, borderRadius: 8, borderWidth: 1, borderColor: colors.borderLight }}
                onPress={() => setOrgAgreed(!orgAgreed)}
              >
                {orgAgreed ? (
                  <CheckSquare size={18} color={colors.brandGreenCourt} style={{ marginTop: 2, marginRight: 8 }} />
                ) : (
                  <Square size={18} color={colors.textMuted} style={{ marginTop: 2, marginRight: 8 }} />
                )}
                <Text style={{ flex: 1, fontSize: 11, color: colors.textSecondary, lineHeight: 16 }}>
                  I agree to uphold the Baseline Society Fair Play & Security standards. I understand all created tournaments and fixtures are auditable.
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.modalSubmitBtn, orgSubmitting && { opacity: 0.6 }]}
                onPress={handleActivateOrganizer}
                disabled={orgSubmitting}
              >
                {orgSubmitting ? (
                  <ActivityIndicator color={colors.brandGold} size="small" />
                ) : (
                  <Text style={styles.modalSubmitText}>ACTIVATE ORGANIZER STATUS</Text>
                )}
              </TouchableOpacity>
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.canvasLight,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  title: {
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 1.5,
    color: colors.brandGreenDeep,
  },
  subtitle: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 1,
    color: colors.brandGold,
    marginTop: 2,
  },
  badgeRank: {
    backgroundColor: colors.brandGreenDeep,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  badgeRankText: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.brandGold,
  },
  content: {
    padding: 20,
    paddingBottom: 30,
  },
  profileCard: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.borderLight,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.brandGreenCourt,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  avatarText: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.brandGold,
  },
  profileDetails: {
    flex: 1,
  },
  playerName: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.textPrimary,
  },
  playerRole: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  playerClub: {
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 2,
  },
  statsGrid: {
    flexDirection: 'row',
    marginTop: 14,
    gap: 8,
  },
  statBox: {
    flex: 1,
    backgroundColor: colors.surfaceCard,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingVertical: 12,
    alignItems: 'center',
  },
  statNum: {
    fontSize: 18,
    fontWeight: '900',
    color: colors.brandGreenDeep,
    fontFamily: 'monospace',
  },
  statLabel: {
    fontSize: 8,
    fontWeight: '800',
    letterSpacing: 0.8,
    color: colors.textSecondary,
    marginTop: 4,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.2,
    color: colors.textSecondary,
    marginTop: 22,
    marginBottom: 8,
  },
  settingsGroup: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingHorizontal: 14,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceSecondary,
  },
  settingTextCol: {
    flex: 1,
    paddingRight: 10,
  },
  settingLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  settingSub: {
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 2,
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceSecondary,
  },
  actionLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.textPrimary,
    marginLeft: 10,
  },
  chevron: {
    marginLeft: 'auto',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    padding: 20,
  },
  modalCard: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: colors.borderLight,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 8,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceSecondary,
    paddingBottom: 10,
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1,
    color: colors.brandGreenDeep,
  },
  modalSubtitle: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.8,
    color: colors.brandGold,
    marginTop: 2,
  },
  closeBtn: {
    padding: 4,
  },
  fieldLabel: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
    color: colors.textSecondary,
    marginTop: 10,
    marginBottom: 4,
  },
  modalInput: {
    backgroundColor: colors.canvasLight,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 13,
    color: colors.textPrimary,
  },
  rolePicker: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 4,
  },
  roleChip: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderLight,
    backgroundColor: colors.canvasLight,
    alignItems: 'center',
  },
  roleChipActive: {
    backgroundColor: colors.brandGreenDeep,
    borderColor: colors.brandGreenDeep,
  },
  roleChipText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.textSecondary,
  },
  roleChipTextActive: {
    color: colors.brandGold,
  },
  modalSubmitBtn: {
    backgroundColor: colors.brandGreenDeep,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 18,
  },
  modalSubmitText: {
    color: colors.brandGold,
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1,
  },
});

