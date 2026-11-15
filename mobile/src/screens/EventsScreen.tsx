import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  RefreshControl,
  SafeAreaView,
} from 'react-native';
import { Search, MapPin, Calendar, Trophy, ChevronRight, Filter } from 'lucide-react-native';
import { colors } from '../theme/colors';
import { useAuthStore } from '../state/authStore';

export default function EventsScreen({ navigation }: any) {
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSurface, setSelectedSurface] = useState('All');
  const { activeRole, setActiveRole } = useAuthStore();

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
    <SafeAreaView style={styles.container}>
      {/* Top Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.appTitle}>BASELINE</Text>
          <Text style={styles.societySub}>THE BASELINE SOCIETY • CHAMPIONSHIP CIRCUIT</Text>
        </View>
        <TouchableOpacity style={styles.badgeClub}>
          <Text style={styles.badgeClubText}>EST. 2026</Text>
        </TouchableOpacity>
      </View>

      {/* Role Experience Switcher Bar */}
      <View style={styles.roleBar}>
        <Text style={styles.roleLabel}>VIEWING AS:</Text>
        <View style={styles.rolePills}>
          {(['organizer', 'player', 'umpire', 'spectator'] as const).map((r) => {
            const isSelected = activeRole === (r === 'organizer' ? 'admin' : r);
            return (
              <TouchableOpacity
                key={r}
                style={[styles.rolePill, isSelected && styles.rolePillActive]}
                onPress={() => setActiveRole(r === 'organizer' ? 'admin' : r)}
              >
                <Text style={[styles.rolePillText, isSelected && styles.rolePillTextActive]}>
                  {r.toUpperCase()}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
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
  appTitle: {
    fontFamily: colors.brandGreenCourt,
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 2,
    color: colors.brandGreenDeep,
  },
  societySub: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 1.2,
    color: colors.brandGold,
    marginTop: 2,
  },
  badgeClub: {
    backgroundColor: colors.brandGreenDeep,
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 6,
  },
  badgeClubText: {
    color: colors.brandGold,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
  },
  roleBar: {
    backgroundColor: colors.surfaceSecondary,
    paddingVertical: 8,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  roleLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.textSecondary,
    letterSpacing: 1,
  },
  rolePills: {
    flexDirection: 'row',
    gap: 4,
  },
  rolePill: {
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 4,
    backgroundColor: 'transparent',
  },
  rolePillActive: {
    backgroundColor: colors.brandGreenDeep,
  },
  rolePillText: {
    fontSize: 9,
    fontWeight: '700',
    color: colors.textSecondary,
  },
  rolePillTextActive: {
    color: colors.brandGold,
  },
  searchSection: {
    paddingHorizontal: 20,
    paddingTop: 14,
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
