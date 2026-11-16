import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  RefreshControl,
  Image,
  ActivityIndicator,
  Modal,
  Alert,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  Search,
  MapPin,
  Calendar,
  Trophy,
  ChevronRight,
  Shield,
  CheckCircle2,
  KeyRound,
  LogOut,
  AlertCircle,
  Plus,
  X,
  Sparkles,
} from 'lucide-react-native';
import { colors } from '../theme/colors';
import { useAuthStore } from '../state/authStore';
import { apiClient } from '../api/client';

export interface TournamentItem {
  id: number;
  name: string;
  slug: string;
  surface: string;
  venue: string;
  city?: string;
  status: string;
  is_live: boolean;
  dates: string;
  entryFee: string;
  categoriesCount: number;
  registeredCount: number;
}

export default function EventsScreen({ navigation }: any) {
  const insets = useSafeAreaInsets();
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tournaments, setTournaments] = useState<TournamentItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSurface, setSelectedSurface] = useState('All');
  const { activeRole, setActiveRole, user, logout } = useAuthStore();

  // Create Tournament Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createVenue, setCreateVenue] = useState('');
  const [createCity, setCreateCity] = useState('');
  const [createSurface, setCreateSurface] = useState('Hard');
  const [createStartDate, setCreateStartDate] = useState('');
  const [createNumCourts, setCreateNumCourts] = useState('2');
  const [creating, setCreating] = useState(false);

  const surfaces = ['All', 'Clay 🧱', 'Hard 🎾', 'Grass 🌱'];

  const handleCreateTournament = async () => {
    if (!createName.trim() || createName.trim().length < 3) {
      Alert.alert('Required', 'Please enter a tournament name (at least 3 characters).');
      return;
    }
    setCreating(true);
    try {
      const res = await apiClient.post('/tournaments', {
        name: createName.trim(),
        venue: createVenue.trim() || 'Baseline Tennis Center',
        city: createCity.trim() || 'Mumbai',
        surface: createSurface,
        start_date: createStartDate.trim() || undefined,
        num_courts: parseInt(createNumCourts, 10) || 2,
      });
      if (res.data?.success) {
        Alert.alert('Tournament Created!', 'Your tournament has been published and is open for registrations.');
        setIsCreateModalOpen(false);
        setCreateName('');
        setCreateVenue('');
        setCreateCity('');
        setCreateStartDate('');
        await fetchTournaments();
      } else {
        Alert.alert('Creation Failed', res.data?.message || 'Could not create tournament');
      }
    } catch (err: any) {
      Alert.alert('Error', err.response?.data?.message || 'Failed to create tournament.');
    } finally {
      setCreating(false);
    }
  };

  const fetchTournaments = async () => {
    try {
      const res = await apiClient.get('/tournaments');
      if (res.data?.success && Array.isArray(res.data.tournaments)) {
        setTournaments(res.data.tournaments);
      } else {
        setTournaments([]);
      }
    } catch {
      setTournaments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTournaments();
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchTournaments();
    setRefreshing(false);
  };

  const filteredEvents = tournaments.filter((event) => {
    const matchesSearch =
      event.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      event.venue.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (event.city && event.city.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchesSearch) return false;

    if (selectedSurface === 'All') return true;
    if (selectedSurface.includes('Clay')) return (event.surface || '').toLowerCase().includes('clay');
    if (selectedSurface.includes('Hard')) return (event.surface || '').toLowerCase().includes('hard');
    if (selectedSurface.includes('Grass')) return (event.surface || '').toLowerCase().includes('grass');
    return true;
  });

  const featuredEvent = tournaments.find((t) => t.is_live) || tournaments[0] || null;

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
          {(activeRole === 'admin' || user?.role === 'admin' || user?.role === 'superadmin') && (
            <TouchableOpacity
              style={styles.btnHostHeader}
              onPress={() => setIsCreateModalOpen(true)}
            >
              <Plus size={13} color={colors.brandGreenDeep} />
              <Text style={styles.btnHostHeaderText}>HOST</Text>
            </TouchableOpacity>
          )}
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
              Organizer dashboard active. Manage entries, publish draws, and schedule matches.
            </Text>
            <View style={styles.adminActionsRow}>
              <TouchableOpacity
                style={[styles.btnAdminAction, { backgroundColor: colors.brandGold, borderColor: colors.brandGold }]}
                onPress={() => setIsCreateModalOpen(true)}
              >
                <Plus size={14} color={colors.brandGreenDeep} />
                <Text style={[styles.btnAdminActionText, { color: colors.brandGreenDeep, fontWeight: '900' }]}>
                  Create Event
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.btnAdminAction}
                onPress={() => navigation.navigate('My Schedule')}
              >
                <Text style={styles.btnAdminActionText}>Order of Play</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.btnAdminAction, { backgroundColor: colors.surfaceCard }]}
                onPress={() => navigation.navigate('Scoring')}
              >
                <Text style={[styles.btnAdminActionText, { color: colors.brandGreenDeep }]}>Court Scoring</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {activeRole === 'player' && (
          <View style={styles.playerBanner}>
            <View style={styles.roleBannerHeader}>
              <CheckCircle2 size={16} color={colors.brandGreenCourt} />
              <Text style={styles.playerBannerTitle}>TOURNAMENT CIRCUIT</Text>
            </View>
            <Text style={styles.playerBannerDetail}>
              Explore sanctioned events, register for categories, and view live order of play.
            </Text>
            <View style={{ flexDirection: 'row', gap: 8, marginTop: 10 }}>
              <TouchableOpacity
                style={[styles.btnPlayerSchedule, { flex: 1 }]}
                onPress={() => navigation.navigate('My Schedule')}
              >
                <Text style={styles.btnPlayerScheduleText}>Court Schedules →</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.btnPlayerSchedule, { flex: 1, backgroundColor: colors.brandGreenDeep, borderWidth: 1, borderColor: colors.brandGold }]}
                onPress={() => setIsCreateModalOpen(true)}
              >
                <Text style={[styles.btnPlayerScheduleText, { color: colors.brandGold, fontWeight: '800' }]}>+ Host Tournament</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {activeRole === 'umpire' && (
          <View style={styles.umpireBanner}>
            <View style={styles.roleBannerHeader}>
              <KeyRound size={16} color="#2B6CB0" />
              <Text style={styles.umpireBannerTitle}>COURT OFFICIAL MODE</Text>
            </View>
            <Text style={styles.umpireBannerSub}>
              Ready to record official game and tiebreak scores on assigned courts.
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

        {/* Featured Live Banner (only if live or upcoming tournament exists) */}
        {featuredEvent && (
          <View style={styles.featuredCard}>
            <View style={styles.liveTagRow}>
              <View style={styles.livePulse} />
              <Text style={styles.liveTagText}>
                {featuredEvent.is_live ? 'CURRENTLY LIVE • OFFICIAL CIRCUIT' : 'FEATURED TOURNAMENT'}
              </Text>
            </View>
            <Text style={styles.featuredTitle}>{featuredEvent.name}</Text>
            <Text style={styles.featuredMeta}>
              {featuredEvent.venue} • {featuredEvent.dates || 'Dates TBA'}
            </Text>
            <TouchableOpacity
              style={styles.btnWatchLive}
              onPress={() => navigation.navigate('My Schedule', { slug: featuredEvent.slug })}
            >
              <Text style={styles.btnWatchLiveText}>View Order of Play & Draws</Text>
              <ChevronRight size={16} color={colors.brandGreenDeep} />
            </TouchableOpacity>
          </View>
        )}

        {/* Tournament Cards List */}
        <View style={styles.listSection}>
          <Text style={styles.sectionHeader}>ALL TOURNAMENTS ({filteredEvents.length})</Text>

          {loading ? (
            <View style={{ paddingVertical: 40, alignItems: 'center' }}>
              <ActivityIndicator color={colors.brandGreenDeep} size="large" />
              <Text style={{ marginTop: 12, color: colors.textSecondary, fontSize: 13 }}>
                Loading circuit events...
              </Text>
            </View>
          ) : filteredEvents.length === 0 ? (
            <View style={{ backgroundColor: colors.surfaceCard, borderRadius: 12, padding: 24, alignItems: 'center', borderWidth: 1, borderColor: colors.borderLight, marginVertical: 10 }}>
              <AlertCircle size={32} color={colors.textMuted} style={{ marginBottom: 10 }} />
              <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
                No Tournaments Found
              </Text>
              <Text style={{ fontSize: 12, color: colors.textSecondary, textAlign: 'center', lineHeight: 18 }}>
                {tournaments.length === 0
                  ? 'There are currently no active tournaments in the database. New events will appear here once published by organizers.'
                  : 'No tournaments match your current filter. Try adjusting your search query or surface filter.'}
              </Text>
            </View>
          ) : (
            filteredEvents.map((event) => (
              <TouchableOpacity
                key={event.id}
                style={styles.card}
                activeOpacity={0.88}
                onPress={() => navigation.navigate('My Schedule', { slug: event.slug })}
              >
                <View style={styles.cardHeader}>
                  <View style={styles.statusBadge}>
                    <Text style={styles.statusText}>{(event.status || 'Active').toUpperCase()}</Text>
                  </View>
                  <Text style={styles.feeBadge}>{event.entryFee} Entry</Text>
                </View>

                <Text style={styles.cardTitle}>{event.name}</Text>

                <View style={styles.cardRow}>
                  <Calendar size={14} color={colors.textSecondary} />
                  <Text style={styles.cardDetail}>{event.dates || 'Dates TBA'}</Text>
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
            ))
          )}
        </View>
      </ScrollView>

      {/* Floating Action Button for Organizers */}
      {(activeRole === 'admin' || user?.role === 'admin' || user?.role === 'superadmin') && (
        <TouchableOpacity
          style={styles.fab}
          onPress={() => setIsCreateModalOpen(true)}
          activeOpacity={0.85}
        >
          <Plus size={20} color={colors.brandGreenDeep} />
          <Text style={styles.fabText}>CREATE EVENT</Text>
        </TouchableOpacity>
      )}

      {/* Create Tournament Modal */}
      <Modal
        visible={isCreateModalOpen}
        animationType="slide"
        transparent
        onRequestClose={() => setIsCreateModalOpen(false)}
      >
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Sparkles size={16} color={colors.brandGold} />
                  <Text style={styles.modalTitle}>HOST TOURNAMENT</Text>
                </View>
                <Text style={styles.modalSubtitle}>Sanction & publish an official event</Text>
              </View>
              <TouchableOpacity
                style={styles.modalCloseBtn}
                onPress={() => setIsCreateModalOpen(false)}
              >
                <X size={20} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false} style={{ maxHeight: 420 }}>
              <Text style={styles.formLabel}>TOURNAMENT NAME *</Text>
              <TextInput
                style={styles.formInput}
                placeholder="e.g. Baseline Championship 2026"
                placeholderTextColor={colors.textMuted}
                value={createName}
                onChangeText={setCreateName}
              />

              <Text style={styles.formLabel}>VENUE / TENNIS CLUB</Text>
              <TextInput
                style={styles.formInput}
                placeholder="e.g. Baseline Tennis Center"
                placeholderTextColor={colors.textMuted}
                value={createVenue}
                onChangeText={setCreateVenue}
              />

              <View style={{ flexDirection: 'row', gap: 10 }}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.formLabel}>CITY</Text>
                  <TextInput
                    style={styles.formInput}
                    placeholder="e.g. Mumbai"
                    placeholderTextColor={colors.textMuted}
                    value={createCity}
                    onChangeText={setCreateCity}
                  />
                </View>
                <View style={{ width: 100 }}>
                  <Text style={styles.formLabel}>COURTS</Text>
                  <TextInput
                    style={styles.formInput}
                    keyboardType="number-pad"
                    placeholder="2"
                    placeholderTextColor={colors.textMuted}
                    value={createNumCourts}
                    onChangeText={setCreateNumCourts}
                  />
                </View>
              </View>

              <Text style={styles.formLabel}>START DATE (YYYY-MM-DD)</Text>
              <TextInput
                style={styles.formInput}
                placeholder="YYYY-MM-DD (e.g. 2026-12-01)"
                placeholderTextColor={colors.textMuted}
                value={createStartDate}
                onChangeText={setCreateStartDate}
              />

              <Text style={styles.formLabel}>SURFACE</Text>
              <View style={styles.surfacePillsRow}>
                {['Hard', 'Clay', 'Grass'].map((s) => (
                  <TouchableOpacity
                    key={s}
                    style={[styles.surfacePill, createSurface === s && styles.surfacePillActive]}
                    onPress={() => setCreateSurface(s)}
                  >
                    <Text
                      style={[
                        styles.surfacePillText,
                        createSurface === s && styles.surfacePillTextActive,
                      ]}
                    >
                      {s === 'Hard' ? 'Hard 🎾' : s === 'Clay' ? 'Clay 🧱' : 'Grass 🌱'}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>

            <View style={styles.modalActionsRow}>
              <TouchableOpacity
                style={styles.btnModalCancel}
                onPress={() => setIsCreateModalOpen(false)}
                disabled={creating}
              >
                <Text style={styles.btnModalCancelText}>CANCEL</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.btnModalSubmit}
                onPress={handleCreateTournament}
                disabled={creating}
              >
                {creating ? (
                  <ActivityIndicator color={colors.brandGreenDeep} size="small" />
                ) : (
                  <Text style={styles.btnModalSubmitText}>PUBLISH EVENT</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
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
  btnHostHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: colors.brandGold,
    paddingVertical: 5,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  btnHostHeaderText: {
    fontSize: 10,
    fontWeight: '900',
    color: colors.brandGreenDeep,
    letterSpacing: 0.8,
  },
  fab: {
    position: 'absolute',
    bottom: 24,
    right: 20,
    backgroundColor: colors.brandGold,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderRadius: 30,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
  },
  fabText: {
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 1,
    color: colors.brandGreenDeep,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalCard: {
    width: '100%',
    backgroundColor: colors.surfaceCard,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: colors.borderLight,
    padding: 20,
    elevation: 10,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 1.2,
    color: colors.brandGreenDeep,
  },
  modalSubtitle: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 2,
  },
  modalCloseBtn: {
    padding: 4,
  },
  formLabel: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
    color: colors.textSecondary,
    marginBottom: 6,
    marginTop: 10,
  },
  formInput: {
    backgroundColor: colors.canvasLight,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 13,
    color: colors.textPrimary,
    fontWeight: '600',
  },
  surfacePillsRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 4,
  },
  surfacePill: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderLight,
    backgroundColor: colors.canvasLight,
    alignItems: 'center',
  },
  surfacePillActive: {
    backgroundColor: colors.brandGreenDeep,
    borderColor: colors.brandGreenDeep,
  },
  surfacePillText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.textSecondary,
  },
  surfacePillTextActive: {
    color: colors.brandGold,
  },
  modalActionsRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 18,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.borderLight,
  },
  btnModalCancel: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderLight,
    alignItems: 'center',
    backgroundColor: colors.canvasLight,
  },
  btnModalCancelText: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    color: colors.textSecondary,
  },
  btnModalSubmit: {
    flex: 2,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: colors.brandGold,
    alignItems: 'center',
  },
  btnModalSubmitText: {
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1,
    color: colors.brandGreenDeep,
  },
});
