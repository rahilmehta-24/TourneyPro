import React, { useState, useEffect, useContext } from 'react';
import { View, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { Appbar, Card, Text, Button, useTheme } from 'react-native-paper';
import { AuthContext } from '../navigation/AuthContext';
import { fetchTournaments } from '../services/api';
import SportsLoader from '../components/SportsLoader';

export default function DashboardScreen({ navigation }) {
  const { user, logout } = useContext(AuthContext);
  const theme = useTheme();
  
  const [tournaments, setTournaments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadTournaments = async () => {
    try {
      const response = await fetchTournaments();
      if (response.success) {
        setTournaments(response.tournaments);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadTournaments();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadTournaments();
  };

  const renderTournament = ({ item }) => (
    <Card 
      style={styles.card} 
      onPress={() => navigation.navigate('TournamentDetail', { tournament: item })}
    >
      <Card.Title 
        title={item.name} 
        subtitle={`Status: ${item.status}`} 
        titleVariant="titleLarge"
      />
      <Card.Content>
        <Text variant="bodyMedium">Categories: {item.categories?.length || 0}</Text>
      </Card.Content>
    </Card>
  );

  if (loading) {
    return <SportsLoader />;
  }

  return (
    <View style={styles.container}>
      <Appbar.Header style={{ backgroundColor: theme.colors.surface }}>
        <Appbar.Content title="Dashboard" />
        <Appbar.Action icon="logout" onPress={logout} />
      </Appbar.Header>

      <FlatList
        data={tournaments}
        keyExtractor={(item) => item.id.toString()}
        renderItem={renderTournament}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primary} />
        }
        ListEmptyComponent={
          <View style={styles.center}>
            <Text>No tournaments found.</Text>
          </View>
        }
      />
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
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  }
});
