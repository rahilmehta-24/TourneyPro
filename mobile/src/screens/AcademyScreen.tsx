import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
} from 'react-native';
import { Users, Award, Bell, ChevronRight } from 'lucide-react-native';
import { colors } from '../theme/colors';

export default function AcademyScreen() {
  const announcements = [
    {
      id: 1,
      title: 'Monsoon High-Performance Camp',
      date: '14 Nov 2026',
      desc: 'Intensive matchplay drill sessions with Coach R. Mehra starting this Saturday.',
    },
    {
      id: 2,
      title: 'Court 1 & 2 Resurfacing Complete',
      date: '10 Nov 2026',
      desc: 'Clay relaid and laser-leveled. Standard footwear required at all times.',
    },
  ];

  const rankings = [
    { rank: 1, name: 'Aarav Mehta', points: 1420, change: '▲ 2' },
    { rank: 2, name: 'Vihaan Patel', points: 1380, change: '▬' },
    { rank: 3, name: 'Kabir Sharma', points: 1290, change: '▼ 1' },
    { rank: 4, name: 'Rohan Nair', points: 1140, change: '▲ 3' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>ACADEMY & CLUB</Text>
          <Text style={styles.subtitle}>SOUTH MUMBAI LAWN TENNIS CLUB • MEMBER HUB</Text>
        </View>
        <View style={styles.memberBadge}>
          <Text style={styles.memberBadgeText}>ACTIVE</Text>
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
        {/* Club Announcements */}
        <Text style={styles.sectionTitle}>BULLETIN & NOTICES</Text>
        {announcements.map((item) => (
          <View key={item.id} style={styles.noticeCard}>
            <View style={styles.noticeHeader}>
              <Text style={styles.noticeTitle}>{item.title}</Text>
              <Text style={styles.noticeDate}>{item.date}</Text>
            </View>
            <Text style={styles.noticeDesc}>{item.desc}</Text>
          </View>
        ))}

        {/* Club Ladder / Rankings */}
        <View style={styles.rankingsHeader}>
          <Text style={styles.sectionTitle}>LADDER RANKINGS (NOV 2026)</Text>
          <TouchableOpacity>
            <Text style={styles.linkText}>View All</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.rankingsCard}>
          {rankings.map((r, i) => (
            <View key={r.rank} style={[styles.rankRow, i > 0 && styles.rankRowBorder]}>
              <View style={styles.rankBadge}>
                <Text style={styles.rankNum}>{r.rank}</Text>
              </View>
              <View style={styles.rankNameCol}>
                <Text style={styles.rankName}>{r.name}</Text>
                <Text style={styles.rankChange}>{r.change}</Text>
              </View>
              <Text style={styles.rankPoints}>{r.points} pts</Text>
            </View>
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
  memberBadge: {
    backgroundColor: colors.brandGreenSubtle,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  memberBadgeText: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.brandGreenCourt,
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
  rankingsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 14,
  },
  linkText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.brandClay,
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
