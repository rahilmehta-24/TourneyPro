import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  SafeAreaView,
  Alert,
} from 'react-native';
import { User, Bell, Shield, Trash2, LogOut, Award, ChevronRight } from 'lucide-react-native';
import { colors } from '../theme/colors';
import { useAuthStore } from '../state/authStore';

export default function ProfileScreen() {
  const { user, logout, activeRole, setActiveRole } = useAuthStore();

  const [notifyMatchCall, setNotifyMatchCall] = useState(true);
  const [notifyDraws, setNotifyDraws] = useState(true);
  const [notifyResults, setNotifyResults] = useState(true);

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
            await logout();
            Alert.alert('Account Deleted', 'Your account and PII have been scrubbed successfully.');
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>PLAYER PROFILE</Text>
          <Text style={styles.subtitle}>BASELINE SOCIETY ID #BS-2026-084</Text>
        </View>
        <TouchableOpacity style={styles.badgeRank}>
          <Text style={styles.badgeRankText}>RANK #4</Text>
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
        {/* Player Profile Card */}
        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>RN</Text>
          </View>
          <View style={styles.profileDetails}>
            <Text style={styles.playerName}>Rafael Nadal</Text>
            <Text style={styles.playerRole}>Senior Member • Left-Handed</Text>
            <Text style={styles.playerClub}>South Mumbai Lawn Tennis Club</Text>
          </View>
        </View>

        {/* Career Stats Grid */}
        <View style={styles.statsGrid}>
          <View style={styles.statBox}>
            <Text style={styles.statNum}>18</Text>
            <Text style={styles.statLabel}>PLAYED</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={[styles.statNum, { color: colors.brandGreenCourt }]}>15</Text>
            <Text style={styles.statLabel}>WON</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={[styles.statNum, { color: colors.brandClay }]}>3</Text>
            <Text style={styles.statLabel}>LOST</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={[styles.statNum, { color: colors.brandGold }]}>83%</Text>
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
              onValueChange={setNotifyMatchCall}
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
              onValueChange={setNotifyDraws}
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
              onValueChange={setNotifyResults}
              trackColor={{ false: colors.surfaceSecondary, true: colors.brandGreenCourt }}
            />
          </View>
        </View>

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
    </SafeAreaView>
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
});

