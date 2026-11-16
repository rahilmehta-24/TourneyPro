import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Clock, CheckCircle2, Activity, Calendar } from 'lucide-react-native';
import { colors } from '../theme/colors';
import { apiClient } from '../api/client';

interface ScheduleMatch {
  id: number;
  court: string;
  round_name: string;
  category_name?: string;
  time_display?: string;
  time?: string;
  is_not_before: boolean;
  status: string;
  score1?: string;
  score2?: string;
  p1: string;
  p2: string;
  winner_id?: number | null;
  winner_name?: string;
  p1_id?: number | null;
  p2_id?: number | null;
}

export default function MyScheduleScreen() {
  const insets = useSafeAreaInsets();
  const [activeCourt, setActiveCourt] = useState('All');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [tournamentName, setTournamentName] = useState<string | null>(null);
  const [courts, setCourts] = useState<string[]>(['All']);
  const [matches, setMatches] = useState<ScheduleMatch[]>([]);

  const fetchSchedule = useCallback(async () => {
    try {
      // 1. Fetch available tournaments
      const tourneyRes = await apiClient.get('/tournaments');
      const tourneys = tourneyRes.data?.tournaments || [];

      if (!tourneys || tourneys.length === 0) {
        setTournamentName(null);
        setCourts(['All']);
        setMatches([]);
        return;
      }

      // Pick live tournament first, else the first upcoming/available one
      const activeTourney = tourneys.find((t: any) => t.is_live || t.status === 'ongoing') || tourneys[0];
      setTournamentName(activeTourney.name);

      // 2. Fetch order of play for this tournament
      const oopRes = await apiClient.get(`/tournaments/${activeTourney.slug}/order-of-play`);
      const serializedCourts = oopRes.data?.courts || [];

      const availableCourts: string[] = ['All'];
      const aggregatedMatches: ScheduleMatch[] = [];

      serializedCourts.forEach((courtGroup: any) => {
        const courtName = courtGroup.court_name;
        if (courtName && !availableCourts.includes(courtName)) {
          availableCourts.push(courtName);
        }

        const courtMatches = courtGroup.matches || [];
        courtMatches.forEach((m: any) => {
          aggregatedMatches.push({
            id: m.id,
            court: courtName,
            round_name: m.round_name || `Round ${m.round}`,
            category_name: m.category_name || 'Tournament Match',
            time_display: m.time_display || m.time || 'TBD',
            time: m.time,
            is_not_before: !!m.is_not_before,
            status: m.status || 'pending',
            score1: m.score1 || '-',
            score2: m.score2 || '-',
            p1: m.participant1?.name || 'TBD',
            p2: m.participant2?.name || 'TBD',
            p1_id: m.participant1?.id,
            p2_id: m.participant2?.id,
            winner_id: m.winner_id,
          });
        });
      });

      setCourts(availableCourts);
      setMatches(aggregatedMatches);
    } catch (err) {
      console.error('Failed to load schedule:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchSchedule();
  }, [fetchSchedule]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchSchedule();
  };

  const filteredMatches = activeCourt === 'All'
    ? matches
    : matches.filter((m) => m.court === activeCourt);

  const activeCourtCount = courts.length > 1 ? courts.length - 1 : 0;

  return (
    <View style={[styles.container, { paddingTop: Math.max(insets.top, 16) }]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={{ flex: 1, marginRight: 8 }}>
          <Text style={styles.title}>ORDER OF PLAY</Text>
          <Text style={styles.subtitle} numberOfLines={1}>
            {tournamentName ? tournamentName.toUpperCase() : 'OFFICIAL TOURNAMENT SCHEDULE'}
          </Text>
        </View>
        {activeCourtCount > 0 && (
          <View style={styles.courtBadge}>
            <Text style={styles.courtBadgeText}>
              {activeCourtCount} {activeCourtCount === 1 ? 'COURT' : 'COURTS'} ACTIVE
            </Text>
          </View>
        )}
      </View>

      {/* Court Selection Tabs */}
      {courts.length > 1 && (
        <View style={styles.tabBar}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
            {courts.map((court) => (
              <TouchableOpacity
                key={court}
                style={[styles.tab, activeCourt === court && styles.tabActive]}
                onPress={() => setActiveCourt(court)}
              >
                <Text style={[styles.tabText, activeCourt === court && styles.tabTextActive]}>
                  {court.toUpperCase()}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      )}

      {loading ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={colors.brandGold} />
          <Text style={styles.loadingText}>Loading court schedules...</Text>
        </View>
      ) : filteredMatches.length === 0 ? (
        <ScrollView
          contentContainerStyle={styles.emptyContainer}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.brandGold} />}
        >
          <View style={styles.emptyIconCircle}>
            <Calendar size={32} color={colors.brandGold} />
          </View>
          <Text style={styles.emptyTitle}>NO MATCHES SCHEDULED</Text>
          <Text style={styles.emptySub}>
            The order of play will appear here once published by the tournament director.
          </Text>
          <TouchableOpacity style={styles.btnRefresh} onPress={onRefresh}>
            <Text style={styles.btnRefreshText}>REFRESH SCHEDULE</Text>
          </TouchableOpacity>
        </ScrollView>
      ) : (
        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.brandGold} />}
        >
          {filteredMatches.map((m) => {
            const isLive = m.status === 'in_progress' || m.status === 'live';
            const isDone = m.status === 'completed';

            return (
              <View key={m.id} style={[styles.matchCard, isLive && styles.matchCardLive]}>
                {/* Card Meta */}
                <View style={styles.cardMeta}>
                  <View style={styles.courtTag}>
                    <Text style={styles.courtTagText}>{m.court}</Text>
                  </View>
                  <View style={styles.timeTag}>
                    <Clock size={12} color={isLive ? colors.statusLive : colors.textSecondary} />
                    <Text style={[styles.timeText, isLive && { color: colors.statusLive, fontWeight: '800' }]}>
                      {m.is_not_before ? `NB ${m.time_display}` : m.time_display}
                    </Text>
                  </View>
                  {isLive && (
                    <View style={styles.liveIndicator}>
                      <Activity size={12} color={colors.statusLive} />
                      <Text style={styles.liveText}>LIVE</Text>
                    </View>
                  )}
                  {isDone && (
                    <View style={styles.doneIndicator}>
                      <CheckCircle2 size={12} color={colors.statusSuccess} />
                      <Text style={styles.doneText}>FINAL</Text>
                    </View>
                  )}
                </View>

                {/* Category */}
                <Text style={styles.categoryText}>
                  {m.category_name} • {m.round_name}
                </Text>

                {/* Players & Scores */}
                <View style={styles.scoreboard}>
                  <View style={styles.playerRow}>
                    <Text
                      style={[
                        styles.playerName,
                        isDone && m.winner_id != null && m.winner_id === m.p1_id ? styles.playerWinner : undefined,
                      ]}
                      numberOfLines={1}
                    >
                      {m.p1}
                    </Text>
                    <Text style={styles.scoreText}>{m.score1}</Text>
                  </View>

                  <View style={styles.divider} />

                  <View style={styles.playerRow}>
                    <Text
                      style={[
                        styles.playerName,
                        isDone && m.winner_id != null && m.winner_id === m.p2_id ? styles.playerWinner : undefined,
                      ]}
                      numberOfLines={1}
                    >
                      {m.p2}
                    </Text>
                    <Text style={styles.scoreText}>{m.score2}</Text>
                  </View>
                </View>

                {/* Status Footer */}
                {isLive && (
                  <View style={styles.liveBanner}>
                    <Text style={styles.liveBannerText}>Match In Progress</Text>
                  </View>
                )}
              </View>
            );
          })}
        </ScrollView>
      )}
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
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
    color: colors.brandGold,
    marginTop: 2,
  },
  courtBadge: {
    backgroundColor: colors.brandGreenSubtle,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  courtBadgeText: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.brandGreenCourt,
  },
  tabBar: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: colors.surfaceSecondary,
  },
  tab: {
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 6,
    backgroundColor: 'transparent',
  },
  tabActive: {
    backgroundColor: colors.brandGreenCourt,
  },
  tabText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.textSecondary,
    letterSpacing: 0.5,
  },
  tabTextActive: {
    color: '#FFFFFF',
  },
  list: {
    padding: 20,
    paddingBottom: 30,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 12,
    fontWeight: '600',
    color: colors.textSecondary,
    letterSpacing: 0.5,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    marginTop: 40,
  },
  emptyIconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.surfaceSecondary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1.2,
    color: colors.brandGreenDeep,
    marginBottom: 8,
  },
  emptySub: {
    fontSize: 12,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 20,
  },
  btnRefresh: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: colors.brandGreenCourt,
    borderRadius: 8,
  },
  btnRefreshText: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    color: '#FFFFFF',
  },
  matchCard: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    padding: 16,
    marginBottom: 14,
  },
  matchCardLive: {
    borderColor: colors.statusLive,
    borderWidth: 1.5,
  },
  cardMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  courtTag: {
    backgroundColor: colors.surfaceSecondary,
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  courtTagText: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.brandGreenCourt,
  },
  timeTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  timeText: {
    fontSize: 11,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  liveIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 'auto',
    backgroundColor: '#FFEAEA',
    paddingVertical: 2,
    paddingHorizontal: 6,
    borderRadius: 4,
    gap: 4,
  },
  liveText: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.statusLive,
  },
  doneIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 'auto',
    gap: 4,
  },
  doneText: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.statusSuccess,
  },
  categoryText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.textSecondary,
    marginBottom: 10,
  },
  scoreboard: {
    backgroundColor: colors.canvasLight,
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  playerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  playerName: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.textPrimary,
    flex: 1,
    marginRight: 12,
  },
  playerWinner: {
    color: colors.brandGreenCourt,
    fontWeight: '900',
  },
  scoreText: {
    fontSize: 14,
    fontWeight: '800',
    fontFamily: 'monospace',
    color: colors.brandGreenDeep,
  },
  divider: {
    height: 1,
    backgroundColor: colors.borderLight,
    marginVertical: 8,
  },
  liveBanner: {
    marginTop: 10,
    paddingVertical: 4,
    paddingHorizontal: 8,
    backgroundColor: '#FFF4E5',
    borderRadius: 6,
  },
  liveBannerText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#B76E00',
  },
});
