import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
} from 'react-native';
import { Clock, CheckCircle2, ChevronRight, Activity } from 'lucide-react-native';
import { colors } from '../theme/colors';

export default function MyScheduleScreen() {
  const [activeCourt, setActiveCourt] = useState('All');

  const courts = ['All', 'Court 1', 'Court 2'];

  const scheduleMatches = [
    {
      id: 1,
      court: 'Court 1',
      round: 'Semi-Final',
      time: '09:00 AM',
      isNotBefore: false,
      status: 'in_progress',
      category: "Men's Singles Open",
      p1: 'R. Federer (1)',
      p2: 'R. Nadal (2)',
      score1: '6  4  •',
      score2: '4  6  •',
      currentSet: 'Set 3 (3-2)',
    },
    {
      id: 2,
      court: 'Court 1',
      round: 'Semi-Final',
      time: '11:30 AM',
      isNotBefore: true,
      status: 'pending',
      category: "Men's Singles Open",
      p1: 'N. Djokovic (3)',
      p2: 'C. Alcaraz (4)',
      score1: '-',
      score2: '-',
      currentSet: 'To Follow',
    },
    {
      id: 3,
      court: 'Court 2',
      round: 'Quarter-Final',
      time: '09:30 AM',
      isNotBefore: false,
      status: 'completed',
      category: "Boys U-18 Singles",
      p1: 'A. Sharma (1)',
      p2: 'V. Patel',
      score1: '6  6',
      score2: '3  2',
      winner: 'A. Sharma',
    },
    {
      id: 4,
      court: 'Court 2',
      round: 'Quarter-Final',
      time: '11:00 AM',
      isNotBefore: false,
      status: 'pending',
      category: "Boys U-18 Singles",
      p1: 'K. Verma',
      p2: 'R. Nair',
      score1: '-',
      score2: '-',
      currentSet: 'Next On Court',
    },
  ];

  const filteredMatches = activeCourt === 'All'
    ? scheduleMatches
    : scheduleMatches.filter((m) => m.court === activeCourt);

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>ORDER OF PLAY</Text>
          <Text style={styles.subtitle}>TODAY • 15 NOV 2026 • OFFICIAL SCHEDULE</Text>
        </View>
        <View style={styles.courtBadge}>
          <Text style={styles.courtBadgeText}>2 COURTS ACTIVE</Text>
        </View>
      </View>

      {/* Court Selection Tabs */}
      <View style={styles.tabBar}>
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
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.list}>
        {filteredMatches.map((m) => {
          const isLive = m.status === 'in_progress';
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
                    {m.isNotBefore ? `NB ${m.time}` : m.time}
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
              <Text style={styles.categoryText}>{m.category} • {m.round}</Text>

              {/* Players & Scores */}
              <View style={styles.scoreboard}>
                <View style={styles.playerRow}>
                  <Text style={[styles.playerName, isDone && m.winner?.includes(m.p1.split(' ')[0]) && styles.playerWinner]}>
                    {m.p1}
                  </Text>
                  <Text style={styles.scoreText}>{m.score1}</Text>
                </View>

                <View style={styles.divider} />

                <View style={styles.playerRow}>
                  <Text style={[styles.playerName, isDone && m.winner?.includes(m.p2.split(' ')[0]) && styles.playerWinner]}>
                    {m.p2}
                  </Text>
                  <Text style={styles.scoreText}>{m.score2}</Text>
                </View>
              </View>

              {/* Status Footer */}
              {isLive && (
                <View style={styles.liveBanner}>
                  <Text style={styles.liveBannerText}>Ongoing: {m.currentSet}</Text>
                </View>
              )}
            </View>
          );
        })}
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
    gap: 8,
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
