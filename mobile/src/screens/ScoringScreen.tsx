import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  SafeAreaView,
  Alert,
} from 'react-native';
import { ShieldCheck, Plus, Minus, KeyRound, Award } from 'lucide-react-native';
import { colors } from '../theme/colors';
import { useAuthStore } from '../state/authStore';

export default function ScoringScreen() {
  const { courtSession, activeRole, loginCourt } = useAuthStore();
  const [pin, setPin] = useState('');
  const [isUnlocked, setIsUnlocked] = useState(false);

  // Scorekeeper state
  const [p1Games, setP1Games] = useState(5);
  const [p2Games, setP2Games] = useState(4);
  const [p1Points, setP1Points] = useState('40');
  const [p2Points, setP2Points] = useState('30');
  const [currentSet, setCurrentSet] = useState(1);
  const [server, setServer] = useState<'p1' | 'p2'>('p1');

  const pointsList = ['0', '15', '30', '40', 'AD'];

  const handleUnlockPin = () => {
    if (pin === '1234' || pin === '123456') {
      setIsUnlocked(true);
      loginCourt({
        court: 'Court 1',
        role: 'official',
        tournament: {
          id: 1,
          name: 'Baseline National Invitational',
          slug: 'baseline-championship',
        },
      }, 'demo_jwt_court_session_token');
    } else {
      Alert.alert('Invalid PIN', 'Please enter a valid Court Official access PIN (e.g. 123456)');
    }
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

  if (!isUnlocked && activeRole !== 'admin') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.pinContainer}>
          <View style={styles.iconCircle}>
            <KeyRound size={32} color={colors.brandGold} />
          </View>
          <Text style={styles.pinTitle}>COURT SCORING MODE</Text>
          <Text style={styles.pinDesc}>
            Enter the 4 to 6 digit Tournament Access PIN provided by the tournament director.
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

          <TouchableOpacity style={styles.btnUnlock} onPress={handleUnlockPin}>
            <Text style={styles.btnUnlockText}>UNLOCK COURT SCORING</Text>
          </TouchableOpacity>

          <Text style={styles.pinHelp}>Demo PIN: 123456</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>LIVE SCOREKEEPER</Text>
          <Text style={styles.subtitle}>COURT 1 • MEN'S SINGLES SF • SET {currentSet}</Text>
        </View>
        <View style={styles.lockBadge}>
          <ShieldCheck size={14} color={colors.statusSuccess} />
          <Text style={styles.lockBadgeText}>v2 SYNCED</Text>
        </View>
      </View>

      <View style={styles.scorerCard}>
        {/* Player 1 Row */}
        <View style={[styles.playerScoreRow, server === 'p1' && styles.serverActiveRow]}>
          <View style={styles.playerInfo}>
            <Text style={styles.scorerPlayerName}>R. Federer</Text>
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
            <Text style={styles.scorerPlayerName}>R. Nadal</Text>
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
          onPress={() => Alert.alert('Score Broadcasted', 'Score updated across tournament displays.')}
        >
          <Text style={styles.actionBtnPrimaryText}>BROADCAST SCORE</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
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
    letterSpacing: 12,
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
  pinHelp: {
    marginTop: 16,
    fontSize: 11,
    color: colors.textMuted,
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
    backgroundColor: colors.brandGreenSubtle,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  lockBadgeText: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.brandGreenCourt,
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
  },
  scorerPlayerName: {
    fontSize: 18,
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

