import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  RefreshControl,
  Image,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Search, MapPin, Calendar, Trophy, ChevronRight, Shield, CheckCircle2, KeyRound, LogOut } from 'lucide-react-native';
import { colors } from '../theme/colors';
import { useAuthStore } from '../state/authStore';

export default function EventsScreen({ navigation }: any) {
  const insets = useSafeAreaInsets();
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSurface, setSelectedSurface] = useState('All');
  const { activeRole, setActiveRole, user, logout } = useAuthStore();

  const surfaces = ['All', 'Clay 🧱', 'Hard 🎾', 'Grass 🌱'];

  const sampleEvents = [
    {
      id: 1,
      name: 'Baseline National Invitational 2026',
      slug: 'baseline-championship',
      dates: 'Nov 15 - 18, 2026',
      surface: 'Clay 🧱',
      venue: 'South Mumbai Lawn Tennis Club',
      status: 'Live & In Progress',
      entryFee: '₹1,500',
      categoriesCount: 6,
      registeredCount: 48,
    },
    {
      id: 2,
      name: 'Monsoon Clay Masters Open',
      slug: 'monsoon-clay-masters',
      dates: 'Dec 02 - 05, 2026',
      surface: 'Clay 🧱',
      venue: 'Singhania Sports Academy, Thane',
      status: 'Registration Open',
      entryFee: '₹1,000',
      categoriesCount: 4,
      registeredCount: 22,
    },
    {
      id: 3,
      name: 'Deccan Hardcourt Junior Trophy',
      slug: 'deccan-junior-trophy',
      dates: 'Dec 12 - 14, 2026',
      surface: 'Hard 🎾',
      venue: 'Deccan Gymkhana, Pune',
      status: 'Upcoming',
      entryFee: '₹800',
      categoriesCount: 8,
      registeredCount: 35,
    },
  ];

  const onRefresh = () => {
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 800);
  };

  return (
    <View style={[styles.container, { paddingTop: Math.max(insets.top, 16) }]}>
      {/* Top Header - Inset safely below Android Status Bar */}
      <View style={styles.header}>
        <View style={styles.headerBrandRow}>
          <Image
            source={require('../../assets/monogram-on-light.png')}
            style={styles.headerMonogram}
          />
          <View style={styles.headerTitles}>
            <Text style={styles.headerAppTitle}>BASELINE</Text>
            <Text style={styles.headerAppSub}>THE BASELINE SOCIETY</Text>
          </View>
        </View>

        <View style={styles.headerRight}>
          <View style={styles.roleChip}>
            <Text style={styles.roleChipText}>
              {activeRole === 'admin'
                ? 'ORGANIZER'
                : activeRole === 'umpire'
                ? 'OFFICIAL'
                : activeRole === 'player'
                ? 'PLAYER'
                : 'GUEST'}
            </Text>
          </View>
          <TouchableOpacity
            style={styles.btnLogoutQuick}
            onPress={() => logout()}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <LogOut size={16} color={colors.textSecondary} />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Role-Specific Executive Banner */}
        {activeRole === 'admin' && (
          <View style={styles.adminBanner}>
            <View style={styles.roleBannerHeader}>
              <Shield size={16} color={colors.brandGold} />
              <Text style={styles.adminBannerTitle}>ORGANIZER COMMAND CENTER</Text>
            </View>
            <Text style={styles.adminBannerSub}>
              3 pending entries awaiting your approval for Baseline National Invitational.
            </Text>
            <View style={styles.adminActionsRow}>
              <TouchableOpacity
                style={styles.btnAdminAction}
                onPress={() => navigation.navigate('My Schedule')}
              >
                <Text style={styles.btnAdminActionText}>Review Entries (3)</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.btnAdminAction, { backgroundColor: colors.surfaceCard }]}
                onPress={() => navigation.navigate('Scoring')}
              >
                <Text style={[styles.btnAdminActionText, { color: colors.brandGreenDeep }]}>Court PINs</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {activeRole === 'player' && (
          <View style={styles.playerBanner}>
            <View style={styles.roleBannerHeader}>
              <CheckCircle2 size={16} color={colors.brandGreenCourt} />
              <Text style={styles.playerBannerTitle}>MY NEXT MATCH TODAY</Text>
            </View>
            <Text style={styles.playerBannerDetail}>
              Men's Singles SF • Court 1 • Scheduled 09:00 AM (vs. R. Nadal)
            </Text>
            <TouchableOpacity
              style={styles.btnPlayerSchedule}
              onPress={() => navigation.navigate('My Schedule')}
            >
              <Text style={styles.btnPlayerScheduleText}>View My Court Schedule →</Text>
            </TouchableOpacity>
          </View>
        )}

        {activeRole === 'umpire' && (
          <View style={styles.umpireBanner}>
            <View style={styles.roleBannerHeader}>
              <KeyRound size={16} color="#2B6CB0" />
              <Text style={styles.umpireBannerTitle}>ASSIGNED COURT: COURT 1</Text>
            </View>
            <Text style={styles.umpireBannerSub}>
              Live Scorekeeper active. Ready to score R. Federer vs R. Nadal.
            </Text>
            <TouchableOpacity
              style={styles.btnUmpireAction}
              onPress={() => navigation.navigate('Scoring')}
            >
              <Text style={styles.btnUmpireActionText}>Open Court Scorekeeper →</Text>
            </TouchableOpacity>
          </View>
        )}

        {activeRole === 'spectator' && (
          <View style={styles.spectatorBanner}>
            <View style={styles.roleBannerHeader}>
              <Trophy size={16} color={colors.brandGold} />
              <Text style={styles.spectatorBannerTitle}>GUEST SPECTATOR MODE</Text>
            </View>
            <Text style={styles.spectatorBannerSub}>
              You are exploring live circuit draws and schedules as a guest.
            </Text>
            <TouchableOpacity
              style={styles.btnSpectatorSignIn}
              onPress={() => logout()}
            >
              <Text style={styles.btnSpectatorSignInText}>Sign In / Register Now →</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Search & Filter */}
        <View style={styles.searchSection}>
          <View style={styles.searchBar}>
            <Search size={18} color={colors.textSecondary} />
            <TextInput
              style={styles.searchInput}
              placeholder="Search tournaments, clubs, venues..."
              placeholderTextColor={colors.textMuted}
              value={searchQuery}
              onChangeText={setSearchQuery}
            />
          </View>
        </View>

        {/* Surface Filter Chips */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipScroll}>
          {surfaces.map((s) => (
            <TouchableOpacity
              key={s}
              style={[styles.chip, selectedSurface === s && styles.chipActive]}
              onPress={() => setSelectedSurface(s)}
            >
              <Text style={[styles.chipText, selectedSurface === s && styles.chipTextActive]}>
                {s}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Featured Live Banner */}
        <View style={styles.featuredCard}>
          <View style={styles.liveTagRow}>
            <View style={styles.livePulse} />
            <Text style={styles.liveTagText}>CURRENTLY LIVE • COURT 1 & 2</Text>
          </View>
          <Text style={styles.featuredTitle}>Baseline National Championship</Text>
          <Text style={styles.featuredMeta}>Men's Singles Quarter-Finals • Center Court</Text>
          <TouchableOpacity
            style={styles.btnWatchLive}
            onPress={() => navigation.navigate('My Schedule')}
          >
            <Text style={styles.btnWatchLiveText}>View Order of Play & Draws</Text>
            <ChevronRight size={16} color={colors.brandGreenDeep} />
          </TouchableOpacity>
        </View>

        {/* Tournament Cards List */}
        <View style={styles.listSection}>
          <Text style={styles.sectionHeader}>ALL TOURNAMENTS ({sampleEvents.length})</Text>

          {sampleEvents.map((event) => (
            <TouchableOpacity
              key={event.id}
              style={styles.card}
              activeOpacity={0.88}
              onPress={() => navigation.navigate('My Schedule', { slug: event.slug })}
            >
              <View style={styles.cardHeader}>
                <View style={styles.statusBadge}>
                  <Text style={styles.statusText}>{event.status.toUpperCase()}</Text>
                </View>
                <Text style={styles.feeBadge}>{event.entryFee} Entry</Text>
              </View>

              <Text style={styles.cardTitle}>{event.name}</Text>

              <View style={styles.cardRow}>
                <Calendar size={14} color={colors.textSecondary} />
                <Text style={styles.cardDetail}>{event.dates}</Text>
              </View>

              <View style={styles.cardRow}>
                <MapPin size={14} color={colors.textSecondary} />
                <Text style={styles.cardDetail}>{event.venue}</Text>
              </View>

              <View style={styles.cardFooter}>
                <Text style={styles.categoryCount}>
                  {event.categoriesCount} Categories • {event.registeredCount} Entries
                </Text>
                <View style={styles.cardArrow}>
                  <ChevronRight size={18} color={colors.brandGreenCourt} />
                </View>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
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
    paddingTop: 8,
    paddingBottom: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  headerBrandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  headerMonogram: {
    width: 36,
    height: 36,
    resizeMode: 'contain',
  },
  headerTitles: {
    justifyContent: 'center',
  },
  headerAppTitle: {
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 2,
    color: colors.brandGreenDeep,
  },
  headerAppSub: {
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 1.2,
    color: colors.brandGreenCourt,
    marginTop: 1,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  roleChip: {
    backgroundColor: colors.brandGreenDeep,
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.brandGold,
  },
  roleChipText: {
    color: colors.brandGold,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 1,
  },
  btnLogoutQuick: {
    width: 34,
    height: 34,
    borderRadius: 8,
    backgroundColor: colors.surfaceSecondary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  spectatorBanner: {
    marginHorizontal: 20,
    marginTop: 12,
    backgroundColor: colors.surfaceCard,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1.5,
    borderColor: colors.brandGold,
  },
  spectatorBannerTitle: {
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1,
    color: colors.brandGreenDeep,
  },
  spectatorBannerSub: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 4,
    lineHeight: 18,
  },
  btnSpectatorSignIn: {
    backgroundColor: colors.brandGreenCourt,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 12,
  },
  btnSpectatorSignInText: {
    color: colors.canvasLight,
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  adminBanner: {
    marginHorizontal: 20,
    marginTop: 12,
    backgroundColor: '#FAF5EB',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1.5,
    borderColor: colors.brandGold,
  },
  roleBannerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  adminBannerTitle: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    color: colors.brandGreenDeep,
  },
  adminBannerSub: {
    fontSize: 12,
    color: colors.textSecondary,
    lineHeight: 18,
    marginBottom: 10,
  },
  adminActionsRow: {
    flexDirection: 'row',
    gap: 10,
  },
  btnAdminAction: {
    backgroundColor: colors.brandGreenDeep,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
  },
  btnAdminActionText: {
    color: colors.brandGold,
    fontSize: 11,
    fontWeight: '800',
  },
  playerBanner: {
    marginHorizontal: 20,
    marginTop: 12,
    backgroundColor: colors.brandGreenSubtle,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1.5,
    borderColor: colors.brandGreenCourt,
  },
  playerBannerTitle: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    color: colors.brandGreenCourt,
  },
  playerBannerDetail: {
    fontSize: 12,
    color: colors.textPrimary,
    fontWeight: '600',
    marginVertical: 4,
  },
  btnPlayerSchedule: {
    marginTop: 4,
  },
  btnPlayerScheduleText: {
    color: colors.brandGreenCourt,
    fontSize: 11,
    fontWeight: '800',
  },
  umpireBanner: {
    marginHorizontal: 20,
    marginTop: 12,
    backgroundColor: '#EBF4FF',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1.5,
    borderColor: '#3182CE',
  },
  umpireBannerTitle: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    color: '#2B6CB0',
  },
  umpireBannerSub: {
    fontSize: 12,
    color: colors.textSecondary,
    marginVertical: 4,
  },
  btnUmpireAction: {
    marginTop: 4,
  },
  btnUmpireActionText: {
    color: '#2B6CB0',
    fontSize: 11,
    fontWeight: '800',
  },
  searchSection: {
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surfaceCard,
    borderWidth: 1,
    borderColor: colors.borderLight,
    borderRadius: 10,
    paddingHorizontal: 12,
    height: 44,
  },
  searchInput: {
    flex: 1,
    marginLeft: 8,
    fontSize: 14,
    color: colors.textPrimary,
  },
  chipScroll: {
    paddingHorizontal: 20,
    marginTop: 12,
    marginBottom: 8,
  },
  chip: {
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 20,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderLight,
    marginRight: 8,
  },
  chipActive: {
    backgroundColor: colors.brandGreenCourt,
    borderColor: colors.brandGreenCourt,
  },
  chipText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  chipTextActive: {
    color: '#FFFFFF',
  },
  featuredCard: {
    marginHorizontal: 20,
    marginTop: 12,
    backgroundColor: colors.brandGreenDeep,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.brandGold,
  },
  liveTagRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  livePulse: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.statusLive,
    marginRight: 6,
  },
  liveTagText: {
    color: '#FF6B6B',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
  },
  featuredTitle: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  featuredMeta: {
    color: colors.borderLight,
    fontSize: 12,
    marginTop: 4,
  },
  btnWatchLive: {
    marginTop: 14,
    backgroundColor: colors.brandGold,
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  btnWatchLiveText: {
    color: colors.brandGreenDeep,
    fontWeight: '800',
    fontSize: 12,
    letterSpacing: 0.5,
  },
  listSection: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 24,
  },
  sectionHeader: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.2,
    color: colors.textSecondary,
    marginBottom: 10,
  },
  card: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    padding: 16,
    marginBottom: 12,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusBadge: {
    backgroundColor: colors.brandGreenSubtle,
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 4,
  },
  statusText: {
    fontSize: 9,
    fontWeight: '800',
    color: colors.brandGreenCourt,
    letterSpacing: 0.5,
  },
  feeBadge: {
    fontSize: 12,
    fontWeight: '800',
    color: colors.brandClay,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.textPrimary,
    marginBottom: 6,
  },
  cardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  cardDetail: {
    fontSize: 12,
    color: colors.textSecondary,
    marginLeft: 6,
  },
  cardFooter: {
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.surfaceSecondary,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  categoryCount: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.textMuted,
  },
  cardArrow: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: colors.surfaceSecondary,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
