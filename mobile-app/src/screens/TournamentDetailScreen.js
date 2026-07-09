import React, { useState, useEffect, useContext } from 'react';
import { View, StyleSheet, SectionList, RefreshControl, Alert, Platform, FlatList } from 'react-native';
import { Appbar, Card, Text, useTheme, ActivityIndicator, Button, Modal, Portal, TextInput, SegmentedButtons } from 'react-native-paper';
import DateTimePicker from '@react-native-community/datetimepicker';
import { AuthContext } from '../navigation/AuthContext';
import { fetchMatches, reportMatch } from '../services/api';
import SportsLoader from '../components/SportsLoader';

export default function TournamentDetailScreen({ route, navigation }) {
  const { tournament } = route.params;
  const { user, token } = useContext(AuthContext);
  const theme = useTheme();
  
  const isAdmin = user && (user.role === 'admin' || user.role === 'superadmin');

  // We simply load matches for the first category for demo purposes.
  // In a full app, you'd have tabs or a selector for categories.
  const activeCategoryId = tournament.categories && tournament.categories.length > 0 
    ? tournament.categories[0].id 
    : null;

  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Modal State
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState(null);
  
  // Form State
  const [status, setStatus] = useState('pending'); // pending, in_progress, completed
  const [score1, setScore1] = useState('');
  const [score2, setScore2] = useState('');
  const [winnerId, setWinnerId] = useState('');
  
  // Date Time Picker State
  const [date, setDate] = useState(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);
  const [isScheduled, setIsScheduled] = useState(false);

  const loadMatches = async () => {
    if (!activeCategoryId) {
      setLoading(false);
      return;
    }
    try {
      const response = await fetchMatches(activeCategoryId);
      if (response.success) {
        const statusPriority = {
          'in_progress': 1,
          'pending': 2,
          'completed': 3
        };

        const sortedMatches = response.matches.sort((a, b) => {
          const priorityA = statusPriority[a.status] || 99;
          const priorityB = statusPriority[b.status] || 99;
          
          if (priorityA !== priorityB) {
            return priorityA - priorityB;
          }
          
          // Secondary sort: round, then match_number
          if (a.round !== b.round) return a.round - b.round;
          return a.match_number - b.match_number;
        });

        const inProgress = sortedMatches.filter(m => m.status === 'in_progress');
        const pending = sortedMatches.filter(m => m.status === 'pending');
        const completed = sortedMatches.filter(m => m.status === 'completed');
        
        const sections = [];
        if (inProgress.length > 0) sections.push({ title: '🔴 LIVE Matches', data: inProgress });
        if (pending.length > 0) sections.push({ title: '⏳ Pending Matches', data: pending });
        if (completed.length > 0) sections.push({ title: '✅ Completed Matches', data: completed });

        setMatches(sections);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadMatches();
  }, [activeCategoryId]);

  const onRefresh = () => {
    setRefreshing(true);
    loadMatches();
  };

  const openMatchModal = (match) => {
    if (!isAdmin) return;
    setSelectedMatch(match);
    setStatus(match.status || 'pending');
    setScore1(match.score1 || '');
    setScore2(match.score2 || '');
    setWinnerId(match.winner_id ? match.winner_id.toString() : '');
    
    if (match.scheduled_time) {
      setDate(new Date(match.scheduled_time));
      setIsScheduled(true);
    } else {
      setDate(new Date());
      setIsScheduled(false);
    }
    
    setModalVisible(true);
  };

  const onChangeDate = (event, selectedDate) => {
    setShowDatePicker(false);
    if (selectedDate) {
      const currentDate = date || new Date();
      selectedDate.setHours(currentDate.getHours());
      selectedDate.setMinutes(currentDate.getMinutes());
      setDate(selectedDate);
      setIsScheduled(true);
    }
  };

  const onChangeTime = (event, selectedTime) => {
    setShowTimePicker(false);
    if (selectedTime) {
      const currentDate = date || new Date();
      currentDate.setHours(selectedTime.getHours());
      currentDate.setMinutes(selectedTime.getMinutes());
      setDate(new Date(currentDate));
      setIsScheduled(true);
    }
  };

  const clearSchedule = () => {
    setIsScheduled(false);
  }

  const handleSubmitScore = async () => {
    if (!selectedMatch) return;

    let actionType = 'pending';
    if (status === 'completed') {
      actionType = 'complete_match';
      if (!winnerId) {
        Alert.alert('Error', 'Please select a winner before completing the match.');
        return;
      }
    } else if (status === 'in_progress') {
      actionType = 'live_score';
    }

    try {
      const scheduledTimeISO = isScheduled ? date.toISOString() : null;
      
      const response = await reportMatch(
        selectedMatch.id, 
        actionType, 
        status, 
        score1, 
        score2, 
        parseInt(winnerId, 10), 
        scheduledTimeISO,
        token
      );

      if (response.success) {
        Alert.alert('Success', 'Match updated successfully');
        setModalVisible(false);
        loadMatches(); // Reload
      } else {
        Alert.alert('Error', response.message);
      }
    } catch (error) {
      Alert.alert('Network Error', 'Failed to submit score');
    }
  };

  const formatScore = (scoreStr) => {
    if (!scoreStr) return '-';
    if (!scoreStr.includes('-')) return scoreStr; // For Bye, W/O, etc.

    return scoreStr.split(', ').map(set => {
      const parts = set.split('-');
      if (parts.length < 2) return set;
      
      let pScore = parts[0].trim();
      let oppScore = parseInt(parts[1], 10);
      
      // If the player scored fewer games, the tiebreak points (in parentheses) belong to them.
      if (parseInt(pScore, 10) < oppScore && parts[1].includes('(')) {
        const tbMatch = parts[1].match(/\(\d+\)/);
        if (tbMatch) {
          pScore += tbMatch[0];
        }
      }
      return pScore;
    }).join('  ');
  };

  const renderMatch = ({ item }) => (
    <Card 
      style={styles.card} 
      onPress={() => openMatchModal(item)}
    >
      <Card.Content>
        <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}}>
          <Text variant="titleMedium" style={{color: theme.colors.primary}}>
            Round {item.round} - Match {item.match_number}
          </Text>
          <Text variant="labelSmall" style={{color: item.status === 'completed' ? '#10b981' : item.status === 'in_progress' ? '#f59e0b' : '#6b7280'}}>
            {item.status.toUpperCase()}
          </Text>
        </View>
        
        {item.scheduled_time && item.status !== 'completed' && (
          <Text variant="bodySmall" style={{marginTop: 4, color: '#9ca3af'}}>
            📅 {new Date(item.scheduled_time).toLocaleString([], {month: 'short', day: 'numeric', hour: '2-digit', minute:'2-digit'})}
          </Text>
        )}

        <View style={styles.matchRow}>
          <Text style={item.winner_id === item.participant1?.id ? styles.winner : {}}>
            {item.participant1 ? item.participant1.name : 'TBD'}
          </Text>
          <Text>{formatScore(item.score1)}</Text>
        </View>
        <View style={styles.matchRow}>
          <Text style={item.winner_id === item.participant2?.id ? styles.winner : {}}>
            {item.participant2 ? item.participant2.name : 'TBD'}
          </Text>
          <Text>{formatScore(item.score2)}</Text>
        </View>
      </Card.Content>
    </Card>
  );

  return (
    <View style={styles.container}>
      <Appbar.Header style={{ backgroundColor: theme.colors.surface }}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title={tournament.name} />
      </Appbar.Header>

      {loading ? (
        <SportsLoader />
      ) : !activeCategoryId ? (
        <View style={styles.center}>
          <Text>No categories in this tournament.</Text>
        </View>
      ) : (
        <SectionList
          sections={matches}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderMatch}
          renderSectionHeader={({ section: { title } }) => (
            <Text variant="titleMedium" style={styles.sectionHeader}>{title}</Text>
          )}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primary} />
          }
        />
      )}

      {/* Admin Match Editing Modal */}
      <Portal>
        <Modal 
          visible={modalVisible} 
          onDismiss={() => setModalVisible(false)} 
          contentContainerStyle={styles.modal}
        >
          {selectedMatch && (
            <FlatList
              data={[{ key: 'form' }]}
              showsVerticalScrollIndicator={false}
              renderItem={() => (
                <View>
                  <Text variant="titleLarge" style={{marginBottom: 16}}>Edit Match</Text>
                  
                  <Text style={{marginBottom: 8}}>Match Status:</Text>
                  <SegmentedButtons
                    value={status}
                    onValueChange={setStatus}
                    style={{marginBottom: 20}}
                    buttons={[
                      { value: 'pending', label: 'Pending' },
                      { value: 'in_progress', label: 'Live' },
                      { value: 'completed', label: 'Finished' },
                    ]}
                  />

                  <Text style={{marginBottom: 8}}>Schedule Time:</Text>
                  <View style={{flexDirection: 'row', alignItems: 'center', marginBottom: 20}}>
                    {isScheduled ? (
                      <View style={{flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between'}}>
                        <Text style={{flex: 1}}>{date.toLocaleString([], {month: 'short', day: 'numeric', hour: '2-digit', minute:'2-digit'})}</Text>
                        <Button mode="text" onPress={() => setShowDatePicker(true)}>Date</Button>
                        <Button mode="text" onPress={() => setShowTimePicker(true)}>Time</Button>
                        <Button mode="text" textColor={theme.colors.error} onPress={clearSchedule}>Clear</Button>
                      </View>
                    ) : (
                      <Button mode="outlined" style={{flex: 1}} onPress={() => setShowDatePicker(true)}>
                        Set Schedule
                      </Button>
                    )}
                  </View>

                  {(showDatePicker || showTimePicker) && (
                    <DateTimePicker
                      value={date}
                      mode={showDatePicker ? 'date' : 'time'}
                      is24Hour={true}
                      display="default"
                      onChange={showDatePicker ? onChangeDate : onChangeTime}
                    />
                  )}

                  {status !== 'pending' && (
                    <>
                      <Text>{selectedMatch.participant1?.name || 'Player 1'} Score:</Text>
                      <TextInput
                        value={score1}
                        onChangeText={setScore1}
                        mode="outlined"
                        style={styles.input}
                      />

                      <Text>{selectedMatch.participant2?.name || 'Player 2'} Score:</Text>
                      <TextInput
                        value={score2}
                        onChangeText={setScore2}
                        mode="outlined"
                        style={styles.input}
                      />
                    </>
                  )}

                  {status === 'completed' && (
                    <>
                      <Text style={{marginBottom: 8, marginTop: 8}}>Select Winner:</Text>
                      <View style={{flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24}}>
                        <Button 
                          mode={winnerId === (selectedMatch.participant1?.id?.toString()) ? "contained" : "outlined"}
                          onPress={() => setWinnerId(selectedMatch.participant1?.id?.toString())}
                          style={{flex: 1, marginRight: 4}}
                          disabled={!selectedMatch.participant1}
                        >
                          {selectedMatch.participant1?.name || 'TBD'}
                        </Button>
                        <Button 
                          mode={winnerId === (selectedMatch.participant2?.id?.toString()) ? "contained" : "outlined"}
                          onPress={() => setWinnerId(selectedMatch.participant2?.id?.toString())}
                          style={{flex: 1, marginLeft: 4}}
                          disabled={!selectedMatch.participant2}
                        >
                          {selectedMatch.participant2?.name || 'TBD'}
                        </Button>
                      </View>
                    </>
                  )}

                  <Button mode="contained" onPress={handleSubmitScore} style={styles.button}>
                    Save Match
                  </Button>
                  <Button mode="text" onPress={() => setModalVisible(false)} style={{marginBottom: 16}}>
                    Cancel
                  </Button>
                </View>
              )}
            />
          )}
        </Modal>
      </Portal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
  },
  list: {
    padding: 16,
    paddingBottom: 40,
  },
  sectionHeader: {
    color: '#9ca3af',
    marginTop: 8,
    marginBottom: 12,
    fontWeight: 'bold',
  },
  card: {
    marginBottom: 16,
    backgroundColor: '#1e1e1e',
  },
  matchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  winner: {
    fontWeight: 'bold',
    color: '#10b981',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modal: {
    backgroundColor: '#1e1e1e',
    padding: 20,
    margin: 20,
    borderRadius: 8,
    maxHeight: '80%',
  },
  input: {
    marginBottom: 16,
  },
  button: {
    marginBottom: 8,
    marginTop: 16,
  }
});
