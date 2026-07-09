import React, { useState, useContext } from 'react';
import { View, StyleSheet, Alert, TextInput as RNTextInput } from 'react-native';
import { Button, Text, Surface, useTheme } from 'react-native-paper';
import { AuthContext } from '../navigation/AuthContext';
import { loginUser } from '../services/api';

export default function LoginScreen() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { login } = useContext(AuthContext);
  const theme = useTheme();

  const handleLogin = async () => {
    if (!username || !password) {
      Alert.alert('Error', 'Please enter both username and password');
      return;
    }

    setLoading(true);
    try {
      const response = await loginUser(username, password);
      if (response.success) {
        login(response.user, response.access_token);
      } else {
        Alert.alert('Login Failed', response.message || 'Invalid credentials');
      }
    } catch (error) {
      Alert.alert('Network Error', 'Could not connect to the server');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Surface style={styles.surface} elevation={4}>
        <Text variant="headlineMedium" style={styles.title}>TourneyPro</Text>
        <Text variant="bodyMedium" style={styles.subtitle}>Sign in to manage tournaments</Text>
        
        <RNTextInput
          placeholder="Username"
          placeholderTextColor="#6b7280"
          onChangeText={(text) => setUsername(text)}
          autoCapitalize="none"
          autoCorrect={false}
          style={[styles.nativeInput, { borderColor: theme.colors.primary }]}
        />
        
        <RNTextInput
          placeholder="Password"
          placeholderTextColor="#6b7280"
          onChangeText={(text) => setPassword(text)}
          secureTextEntry
          autoCapitalize="none"
          autoCorrect={false}
          style={[styles.nativeInput, { borderColor: theme.colors.primary }]}
        />
        
        <Button 
          mode="contained" 
          onPress={handleLogin} 
          loading={loading}
          style={styles.button}
        >
          Login
        </Button>
      </Surface>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
    backgroundColor: '#121212',
  },
  surface: {
    padding: 24,
    borderRadius: 16,
    backgroundColor: '#1e1e1e',
  },
  title: {
    textAlign: 'center',
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#10b981',
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: 24,
    opacity: 0.7,
  },
  nativeInput: {
    height: 50,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 16,
    marginBottom: 16,
    color: '#ffffff',
    backgroundColor: 'transparent',
    fontSize: 16,
  },
  button: {
    marginTop: 8,
    paddingVertical: 6,
  }
});
