import React, { useState, useEffect, useContext } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, Alert } from 'react-native';
import { Appbar, Card, Text, useTheme, ActivityIndicator, Button, Modal, Portal, TextInput } from 'react-native-paper';
import { AuthContext } from '../navigation/AuthContext';
import { fetchMatches, reportMatch } from '../services/api';

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
  const [score1, setScore1] = useState('');
  const [score2, setScore2] = useState('');
  const [winnerId, setWinnerId] = useState('');

  const loadMatches = async () => {
    if (!activeCategoryId) {
      setLoading(false);
      return;
    }
    try {
      const response = await fetchMatches(activeCategoryId);
      if (response.success) {
        setMatches(response.matches);
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
    setScore1(match.score1 || '');
    setScore2(match.score2 || '');
    setWinnerId(match.winner_id ? match.winner_id.toString() : '');
    setModalVisible(true);
  };

  const handleSubmitScore = async () => {
    if (!selectedMatch) return;

    try {
      // In this demo, we assume the match is complete if a winner is selected
      const actionType = 'complete_match';
      const status = 'completed';
      
      const response = await reportMatch(
        selectedMatch.id, 
        actionType, 
        status, 
        score1, 
        score2, 
        parseInt(winnerId, 10), 
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

  const renderMatch = ({ item }) => (
    <Card 
      style={styles.card} 
      onPress={() => openMatchModal(item)}
    >
      <Card.Content>
        <Text variant="titleMedium" style={{color: theme.colors.primary}}>
          Round {item.round} - Match {item.match_number}
        </Text>
        <Text variant="bodyMedium">Status: {item.status}</Text>
        <View style={styles.matchRow}>
          <Text style={item.winner_id === item.participant1?.id ? styles.winner : {}}>
            {item.participant1 ? item.participant1.name : 'TBD'}
          </Text>
          <Text>{item.score1 || '-'}</Text>
        </View>
        <View style={styles.matchRow}>
          <Text style={item.winner_id === item.participant2?.id ? styles.winner : {}}>
            {item.participant2 ? item.participant2.name : 'TBD'}
          </Text>
          <Text>{item.score2 || '-'}</Text>
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
        <View style={styles.center}>
          <ActivityIndicator size="large" />
        </View>
      ) : !activeCategoryId ? (
        <View style={styles.center}>
          <Text>No categories in this tournament.</Text>
        </View>
      ) : (
        <FlatList
          data={matches}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderMatch}
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
            <>
              <Text variant="titleLarge" style={{marginBottom: 16}}>Edit Match</Text>
              
              <Text>{selectedMatch.participant1?.name || 'TBD'} Score:</Text>
              <TextInput
                value={score1}
                onChangeText={setScore1}
                mode="outlined"
                style={styles.input}
              />

              <Text>{selectedMatch.participant2?.name || 'TBD'} Score:</Text>
              <TextInput
                value={score2}
                onChangeText={setScore2}
                mode="outlined"
                style={styles.input}
              />

              <Text>Winner ID (Must match participant ID):</Text>
              <TextInput
                value={winnerId}
                onChangeText={setWinnerId}
                mode="outlined"
                keyboardType="numeric"
                style={styles.input}
              />

              <Button mode="contained" onPress={handleSubmitScore} style={styles.button}>
                Save Score
              </Button>
              <Button mode="text" onPress={() => setModalVisible(false)}>
                Cancel
              </Button>
            </>
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
  },
  input: {
    marginBottom: 16,
  },
  button: {
    marginBottom: 8,
  }
});
