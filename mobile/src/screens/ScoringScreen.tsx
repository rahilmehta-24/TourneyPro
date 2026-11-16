import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ShieldCheck, KeyRound, Award, RefreshCw, LogOut } from 'lucide-react-native';
import { colors } from '../theme/colors';
import { useAuthStore } from '../state/authStore';
import { apiClient } from '../api/client';

interface CourtMatch {
  id: number;
  court: string;
  round_name: string;
  category_name?: string;
  lock_version?: number;
  status: string;
  score1?: string;
  score2?: string;
  participant1?: { id?: number; name?: string };
  participant2?: { id?: number; name?: string };
}

export default function ScoringScreen() {
  const insets = useSafeAreaInsets();
  const { courtSession, activeRole, loginCourt, logout } = useAuthStore();
  const [pin, setPin] = useState('');
  const [loading, setLoading] = useState(false);
  const [isUnlocked, setIsUnlocked] = useState(!!courtSession);
  const [currentMatch, setCurrentMatch] = useState<CourtMatch | null>(null);

  // Scorekeeper state
  const [p1Games, setP1Games] = useState(0);
  const [p2Games, setP2Games] = useState(0);
  const [p1Points, setP1Points] = useState('0');
  const [p2Points, setP2Points] = useState('0');
  const [currentSet, setCurrentSet] = useState(1);
  const [server, setServer] = useState<'p1' | 'p2'>('p1');

  const pointsList = ['0', '15', '30', '40', 'AD'];

  const fetchActiveMatch = useCallback(async (slug?: string, courtName?: string) => {
    const currentSlug = slug || courtSession?.tournament?.slug;
    const currentCourt = courtName || courtSession?.court;
    if (!currentSlug) return;

    try {
      const res = await apiClient.get(`/tournaments/${currentSlug}/order-of-play`, {
        params: currentCourt && currentCourt !== 'All Courts' ? { court: currentCourt } : {},
      });
      const courts = res.data?.courts || [];
      let foundMatch: CourtMatch | null = null;

      for (const courtGroup of courts) {
        if (!currentCourt || currentCourt === 'All Courts' || courtGroup.court_name === currentCourt) {
          const match = courtGroup.matches?.find(
            (m: any) => m.status === 'in_progress' || m.status === 'live' || m.status === 'pending'
          );
          if (match) {
            foundMatch = {
              id: match.id,
              court: courtGroup.court_name,
              round_name: match.round_name,
              category_name: match.category_name,
              lock_version: match.lock_version || 1,
              status: match.status,
              score1: match.score1,
              score2: match.score2,
              participant1: match.participant1,
              participant2: match.participant2,
            };
            break;
          }
        }
      }

      setCurrentMatch(foundMatch);
      if (foundMatch) {
        const s1 = parseInt(foundMatch.score1 || '0', 10);
        const s2 = parseInt(foundMatch.score2 || '0', 10);
        setP1Games(isNaN(s1) ? 0 : s1);
        setP2Games(isNaN(s2) ? 0 : s2);
      }
    } catch (err) {
      console.error('Failed to load court match:', err);
    }
  }, [courtSession]);

  useEffect(() => {
    if (courtSession) {
      setIsUnlocked(true);
      fetchActiveMatch();
    }
  }, [courtSession, fetchActiveMatch]);

  const handleUnlockPin = async () => {
    const cleanPin = pin.trim();
    if (!cleanPin) {
      Alert.alert('Required', 'Please enter your court access PIN.');
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.post('/auth/court-login', { pin: cleanPin });
      if (res.data?.success && res.data?.access_token) {
        await loginCourt(
          {
            court: res.data.court,
            role: res.data.role,
            tournament: res.data.tournament,
          },
          res.data.access_token
        );
        setIsUnlocked(true);
        fetchActiveMatch(res.data.tournament?.slug, res.data.court);
      } else {
        Alert.alert('Access Denied', res.data?.message || 'Invalid access PIN.');
      }
    } catch (err: any) {
      Alert.alert(
        'Authentication Failed',
        err.response?.data?.message || 'Invalid or expired court access PIN.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleEndSession = async () => {
    Alert.alert('Lock Court', 'Are you sure you want to exit court scoring mode?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Lock & Exit',
        style: 'destructive',
        onPress: async () => {
          setIsUnlocked(false);
          setPin('');
          setCurrentMatch(null);
          await logout();
        },
      },
    ]);
  };

  const incrementPoint = (player: 'p1' | 'p2') => {
    const current = player === 'p1' ? p1Points : p2Points;
    const currentIndex = pointsList.indexOf(current);
    if (currentIndex < pointsList.length - 1) {
      if (player === 'p1') setP1Points(pointsList[currentIndex + 1]);
      else setP2Points(pointsList[currentIndex + 1]);
    } else {
      // Game won
      if (player === 'p1') {
        setP1Games((g) => g + 1);
        setP1Points('0');
        setP2Points('0');
      } else {
        setP2Games((g) => g + 1);
        setP1Points('0');
        setP2Points('0');
      }
      setServer((s) => (s === 'p1' ? 'p2' : 'p1'));
    }
  };

  const handleBroadcastScore = async () => {
    if (!currentMatch) {
      Alert.alert('No Match', 'No match is currently assigned to this court.');
      return;
    }
    setLoading(true);
    try {
      await apiClient.post(`/matches/${currentMatch.id}/report`, {
        score1: String(p1Games),
        score2: String(p2Games),
        status: 'in_progress',
        lock_version: currentMatch.lock_version || 1,
      });
      Alert.alert('Score Broadcasted', 'Score synchronized with tournament live center.');
    } catch (err: any) {
      Alert.alert('Sync Notice', err.response?.data?.message || 'Could not synchronize score with server.');
    } finally {
      setLoading(false);
    }
  };

  if (!isUnlocked && activeRole !== 'admin') {
    return (
      <View style={[styles.container, { paddingTop: Math.max(insets.top, 16) }]}>
        <View style={styles.pinContainer}>
          <View style={styles.iconCircle}>
            <KeyRound size={32} color={colors.brandGold} />
          </View>
          <Text style={styles.pinTitle}>COURT SCORING MODE</Text>
          <Text style={styles.pinDesc}>
            Enter the 4 to 6 digit Tournament Access PIN provided by the tournament director to unlock court scorekeeping.
          </Text>

          <TextInput
            style={styles.pinInput}
            keyboardType="number-pad"
            maxLength={6}
            placeholder="• • • • • •"
            placeholderTextColor={colors.textMuted}
            value={pin}
            onChangeText={setPin}
            secureTextEntry
          />

          <TouchableOpacity
            style={styles.btnUnlock}
            onPress={handleUnlockPin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color={colors.brandGold} />
            ) : (
              <Text style={styles.btnUnlockText}>UNLOCK COURT SCORING</Text>
            )}
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  const courtLabel = courtSession?.court || 'COURT';
  const tournamentTitle = courtSession?.tournament?.name || 'LIVE TOURNAMENT';
  const player1Name = currentMatch?.participant1?.name || 'Player 1 (TBD)';
  const player2Name = currentMatch?.participant2?.name || 'Player 2 (TBD)';
  const matchCategory = currentMatch
    ? `${currentMatch.category_name} • ${currentMatch.round_name}`
    : 'No match currently assigned';

  return (
    <View style={[styles.container, { paddingTop: Math.max(insets.top, 16) }]}>
      <View style={styles.header}>
        <View style={{ flex: 1, marginRight: 8 }}>
          <Text style={styles.title}>{courtLabel.toUpperCase()}</Text>
          <Text style={styles.subtitle} numberOfLines={1}>
            {tournamentTitle.toUpperCase()} • SET {currentSet}
          </Text>
        </View>
        <TouchableOpacity style={styles.lockBadge} onPress={handleEndSession}>
          <LogOut size={12} color={colors.statusLive} />
          <Text style={[styles.lockBadgeText, { color: colors.statusLive }]}>EXIT</Text>
        </TouchableOpacity>
      </View>

      {!currentMatch ? (
        <ScrollView contentContainerStyle={styles.emptyCourtContainer}>
          <View style={styles.emptyIconCircle}>
            <Award size={36} color={colors.brandGold} />
          </View>
          <Text style={styles.emptyCourtTitle}>COURT ACTIVE & READY</Text>
          <Text style={styles.emptyCourtSub}>
            No match is currently assigned to {courtLabel}. Assigned matches will appear here automatically when called by the tournament director.
          </Text>
          <TouchableOpacity
            style={styles.btnCheckMatches}
            onPress={() => fetchActiveMatch()}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" size="small" />
            ) : (
              <>
                <RefreshCw size={14} color="#FFFFFF" />
                <Text style={styles.btnCheckMatchesText}>CHECK FOR MATCHES</Text>
              </>
            )}
          </TouchableOpacity>
        </ScrollView>
      ) : (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 30 }}>
          <View style={styles.matchMetaBar}>
            <Text style={styles.matchMetaText}>{matchCategory}</Text>
          </View>

          <View style={styles.scorerCard}>
            {/* Player 1 Row */}
            <View style={[styles.playerScoreRow, server === 'p1' && styles.serverActiveRow]}>
              <View style={styles.playerInfo}>
                <Text style={styles.scorerPlayerName} numberOfLines={1}>
                  {player1Name}
                </Text>
                {server === 'p1' && <Text style={styles.servingBadge}>🎾 SERVING</Text>}
              </View>
              <View style={styles.scoreBlocks}>
                <Text style={styles.gamesBlock}>{p1Games}</Text>
                <TouchableOpacity style={styles.pointsBlock} onPress={() => incrementPoint('p1')}>
                  <Text style={styles.pointsText}>{p1Points}</Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.scoreDivider} />

            {/* Player 2 Row */}
            <View style={[styles.playerScoreRow, server === 'p2' && styles.serverActiveRow]}>
              <View style={styles.playerInfo}>
                <Text style={styles.scorerPlayerName} numberOfLines={1}>
                  {player2Name}
                </Text>
                {server === 'p2' && <Text style={styles.servingBadge}>🎾 SERVING</Text>}
              </View>
              <View style={styles.scoreBlocks}>
                <Text style={styles.gamesBlock}>{p2Games}</Text>
                <TouchableOpacity style={styles.pointsBlock} onPress={() => incrementPoint('p2')}>
                  <Text style={styles.pointsText}>{p2Points}</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>

          {/* Tactile Action Controls */}
          <View style={styles.controlsRow}>
            <TouchableOpacity
              style={styles.actionBtnSecondary}
              onPress={() => {
                setP1Points('0');
                setP2Points('0');
              }}
            >
              <Text style={styles.actionBtnSecondaryText}>RESET GAME</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.actionBtnPrimary}
              onPress={handleBroadcastScore}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color={colors.brandGold} />
              ) : (
                <Text style={styles.actionBtnPrimaryText}>BROADCAST SCORE</Text>
              )}
            </TouchableOpacity>
          </View>
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
  pinContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 30,
  },
  iconCircle: {
    width: 68,
    height: 68,
    borderRadius: 34,
    backgroundColor: colors.brandGreenDeep,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  pinTitle: {
    fontSize: 20,
    fontWeight: '900',
    color: colors.brandGreenDeep,
    letterSpacing: 1.5,
    marginBottom: 8,
  },
  pinDesc: {
    fontSize: 13,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 24,
  },
  pinInput: {
    width: 220,
    height: 52,
    backgroundColor: colors.surfaceCard,
    borderWidth: 1.5,
    borderColor: colors.borderLight,
    borderRadius: 12,
    fontSize: 24,
    letterSpacing: 10,
    textAlign: 'center',
    color: colors.brandGreenDeep,
    fontWeight: '800',
    marginBottom: 20,
  },
  btnUnlock: {
    width: 220,
    height: 48,
    backgroundColor: colors.brandGreenDeep,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  btnUnlockText: {
    color: colors.brandGold,
    fontWeight: '800',
    fontSize: 12,
    letterSpacing: 1,
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
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 1.2,
    color: colors.brandGreenDeep,
  },
  subtitle: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 1,
    color: colors.brandGold,
    marginTop: 2,
  },
  lockBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#FFEAEA',
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 6,
  },
  lockBadgeText: {
    fontSize: 10,
    fontWeight: '800',
  },
  emptyCourtContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
    marginTop: 60,
  },
  emptyIconCircle: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.surfaceSecondary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  emptyCourtTitle: {
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 1.2,
    color: colors.brandGreenDeep,
    marginBottom: 8,
  },
  emptyCourtSub: {
    fontSize: 13,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 24,
  },
  btnCheckMatches: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 20,
    paddingVertical: 12,
    backgroundColor: colors.brandGreenCourt,
    borderRadius: 8,
  },
  btnCheckMatchesText: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    color: '#FFFFFF',
  },
  matchMetaBar: {
    paddingHorizontal: 20,
    paddingTop: 14,
    paddingBottom: 4,
  },
  matchMetaText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.textSecondary,
    letterSpacing: 0.5,
  },
  scorerCard: {
    margin: 20,
    backgroundColor: colors.surfaceCard,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: colors.borderLight,
    padding: 18,
  },
  playerScoreRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  serverActiveRow: {
    backgroundColor: colors.brandGreenSubtle,
    borderRadius: 10,
    paddingHorizontal: 10,
  },
  playerInfo: {
    flex: 1,
    marginRight: 10,
  },
  scorerPlayerName: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.textPrimary,
  },
  servingBadge: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.brandGreenCourt,
    marginTop: 2,
  },
  scoreBlocks: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  gamesBlock: {
    fontSize: 32,
    fontWeight: '900',
    color: colors.textSecondary,
    fontFamily: 'monospace',
    minWidth: 36,
    textAlign: 'center',
  },
  pointsBlock: {
    backgroundColor: colors.brandGreenDeep,
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 10,
    minWidth: 64,
    alignItems: 'center',
  },
  pointsText: {
    color: colors.brandGold,
    fontSize: 22,
    fontWeight: '900',
    fontFamily: 'monospace',
  },
  scoreDivider: {
    height: 1,
    backgroundColor: colors.surfaceSecondary,
    marginVertical: 4,
  },
  controlsRow: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    gap: 12,
  },
  actionBtnSecondary: {
    flex: 1,
    height: 48,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: colors.borderLight,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.surfaceCard,
  },
  actionBtnSecondaryText: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    color: colors.textSecondary,
  },
  actionBtnPrimary: {
    flex: 2,
    height: 48,
    borderRadius: 10,
    backgroundColor: colors.brandGreenDeep,
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionBtnPrimaryText: {
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1,
    color: colors.brandGold,
  },
});
