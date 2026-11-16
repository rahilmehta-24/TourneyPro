import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Award, Bell } from 'lucide-react-native';
import { colors } from '../theme/colors';
import { useAuthStore } from '../state/authStore';
import { apiClient } from '../api/client';

export interface LeaderboardPlayer {
  rank: number;
  id: number;
  name: string;
  points: number;
  academy?: string;
  age_category?: string;
  win_rate?: number;
}

export interface AnnouncementItem {
  id: number;
  title: string;
  desc: string;
  date: string;
  academy_name?: string;
}

export default function AcademyScreen() {
  const insets = useSafeAreaInsets();
  const { player, user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);
  const [rankings, setRankings] = useState<LeaderboardPlayer[]>([]);

  const fetchData = async () => {
    try {
      const [rankingsRes, announcementsRes] = await Promise.allSettled([
        apiClient.get('/leaderboard'),
        apiClient.get('/announcements'),
      ]);

      if (rankingsRes.status === 'fulfilled' && rankingsRes.value.data?.success) {
        setRankings(rankingsRes.value.data.rankings || []);
      } else {
        setRankings([]);
      }

      if (announcementsRes.status === 'fulfilled' && announcementsRes.value.data?.success) {
        setAnnouncements(announcementsRes.value.data.announcements || []);
      } else {
        setAnnouncements([]);
      }
    } catch {
      setRankings([]);
      setAnnouncements([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const academyTitle = player?.academy
    ? `${player.academy.toUpperCase()} • MEMBER HUB`
    : 'THE BASELINE SOCIETY • MEMBER HUB';

  return (
    <View style={[styles.container, { paddingTop: Math.max(insets.top, 16) }]}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>ACADEMY & CLUB</Text>
          <Text style={styles.subtitle}>{academyTitle}</Text>
        </View>
        <View style={styles.memberBadge}>
          <Text style={styles.memberBadgeText}>{user ? 'ACTIVE' : 'GUEST'}</Text>
        </View>
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.brandGreenCourt} />}
      >
        {/* Club Announcements */}
        <Text style={styles.sectionTitle}>BULLETIN & NOTICES</Text>
        {loading ? (
          <View style={{ paddingVertical: 20, alignItems: 'center' }}>
            <ActivityIndicator color={colors.brandGreenDeep} size="small" />
          </View>
        ) : announcements.length === 0 ? (
          <View style={styles.emptyCard}>
            <Bell size={24} color={colors.textMuted} style={{ marginBottom: 6 }} />
            <Text style={styles.emptyTitle}>No Active Notices</Text>
            <Text style={styles.emptyDesc}>
              No bulletin notices have been posted by academies at this time.
            </Text>
          </View>
        ) : (
          announcements.map((item) => (
            <View key={item.id} style={styles.noticeCard}>
              <View style={styles.noticeHeader}>
                <Text style={styles.noticeTitle}>{item.title}</Text>
                <Text style={styles.noticeDate}>{item.date}</Text>
              </View>
              <Text style={styles.noticeDesc}>{item.desc}</Text>
              {item.academy_name && (
                <Text style={styles.noticeAcademy}>Source: {item.academy_name}</Text>
              )}
            </View>
          ))
        )}

        {/* Club Ladder / Rankings */}
        <View style={styles.rankingsHeader}>
          <Text style={styles.sectionTitle}>CIRCUIT LADDER RANKINGS</Text>
        </View>

        {loading ? (
          <View style={{ paddingVertical: 20, alignItems: 'center' }}>
            <ActivityIndicator color={colors.brandGreenDeep} size="small" />
          </View>
        ) : rankings.length === 0 ? (
          <View style={styles.emptyCard}>
            <Award size={24} color={colors.textMuted} style={{ marginBottom: 6 }} />
            <Text style={styles.emptyTitle}>No Ranking Points Yet</Text>
            <Text style={styles.emptyDesc}>
              Official circuit rankings will populate as tournament matches conclude and points are awarded.
            </Text>
          </View>
        ) : (
          <View style={styles.rankingsCard}>
            {rankings.map((r, i) => (
              <View key={r.id || r.rank} style={[styles.rankRow, i > 0 && styles.rankRowBorder]}>
                <View style={styles.rankBadge}>
                  <Text style={styles.rankNum}>{r.rank}</Text>
                </View>
                <View style={styles.rankNameCol}>
                  <Text style={styles.rankName}>{r.name}</Text>
                  <Text style={styles.rankChange}>{r.academy || 'Independent'}</Text>
                </View>
                <Text style={styles.rankPoints}>{r.points} pts</Text>
              </View>
            ))}
          </View>
        )}
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
    letterSpacing: 0.8,
    color: colors.brandGold,
    marginTop: 2,
  },
  memberBadge: {
    backgroundColor: colors.brandGreenDeep,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  memberBadgeText: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.brandGold,
  },
  content: {
    padding: 20,
    paddingBottom: 30,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.2,
    color: colors.textSecondary,
    marginBottom: 10,
    marginTop: 6,
  },
  noticeCard: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    padding: 14,
    marginBottom: 12,
  },
  noticeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  noticeTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: colors.textPrimary,
  },
  noticeDate: {
    fontSize: 10,
    color: colors.textMuted,
    fontWeight: '600',
  },
  noticeDesc: {
    fontSize: 12,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  noticeAcademy: {
    fontSize: 10,
    color: colors.brandGold,
    marginTop: 6,
    fontWeight: '600',
  },
  emptyCard: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    padding: 20,
    alignItems: 'center',
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: 4,
  },
  emptyDesc: {
    fontSize: 11,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 16,
  },
  rankingsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 14,
    marginBottom: 8,
  },
  rankingsCard: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingHorizontal: 14,
    marginTop: 10,
  },
  rankRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
  },
  rankRowBorder: {
    borderTopWidth: 1,
    borderTopColor: colors.surfaceSecondary,
  },
  rankBadge: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colors.surfaceSecondary,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  rankNum: {
    fontSize: 12,
    fontWeight: '800',
    color: colors.brandGreenDeep,
  },
  rankNameCol: {
    flex: 1,
  },
  rankName: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  rankChange: {
    fontSize: 10,
    color: colors.textMuted,
    marginTop: 2,
  },
  rankPoints: {
    fontSize: 13,
    fontWeight: '800',
    fontFamily: 'monospace',
    color: colors.brandGreenDeep,
  },
});
