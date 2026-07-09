import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';

const TENNIS_FACTS = [
  "The longest tennis match in history lasted 11 hours and 5 minutes at Wimbledon in 2010.",
  "Yellow tennis balls were used at Wimbledon for the first time in 1986.",
  "Venus and Serena Williams became the first sisters to win Olympic gold medals in tennis.",
  "The fastest tennis serve on record was hit by Sam Groth at 163.7 mph (263.4 km/h).",
  "A tennis ball is typically in play for only 20 minutes during a 2.5-hour match.",
  "The word 'tennis' comes from the French word 'tenez', meaning 'take' or 'receive'.",
  "Wimbledon is the only Grand Slam tournament played on grass courts.",
  "Arthur Ashe is the only black man ever to win the singles title at Wimbledon, the US Open, and the Australian Open.",
  "Steffi Graf is the only player to achieve the Golden Slam (all 4 Grand Slams and Olympic Gold in the same year)."
];

export default function SportsLoader() {
  const [fact, setFact] = useState('');
  
  // Animation values
  const swingAnim = new Animated.Value(0);
  const flyAnim = new Animated.Value(0);

  useEffect(() => {
    // Pick a random fact
    setFact(TENNIS_FACTS[Math.floor(Math.random() * TENNIS_FACTS.length)]);
    
    // Start animation loop
    Animated.loop(
      Animated.parallel([
        Animated.sequence([
          Animated.timing(swingAnim, {
            toValue: 1,
            duration: 750,
            useNativeDriver: true
          }),
          Animated.timing(swingAnim, {
            toValue: 0,
            duration: 750,
            useNativeDriver: true
          })
        ]),
        Animated.sequence([
          Animated.timing(flyAnim, {
            toValue: 1,
            duration: 1500,
            useNativeDriver: true
          })
        ])
      ])
    ).start();
  }, []);

  const swingInterpolate = swingAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: ['-20deg', '60deg', '-20deg']
  });

  const flyInterpolateX = flyAnim.interpolate({
    inputRange: [0, 0.4, 0.5, 1],
    outputRange: [0, 100, 120, 0]
  });

  const flyInterpolateY = flyAnim.interpolate({
    inputRange: [0, 0.4, 0.5, 1],
    outputRange: [0, -40, -20, 0]
  });

  const flyOpacity = flyAnim.interpolate({
    inputRange: [0, 0.4, 0.5, 1],
    outputRange: [1, 1, 0, 0]
  });

  return (
    <View style={styles.container}>
      <View style={styles.animationContainer}>
        {/* Player */}
        <Text style={[styles.emoji, styles.player]}>🏃‍♂️</Text>
        {/* Racket */}
        <Animated.Text 
          style={[
            styles.emoji, 
            styles.racket, 
            { transform: [{ rotate: swingInterpolate }] }
          ]}
        >
          🏸
        </Animated.Text>
        {/* Ball */}
        <Animated.Text 
          style={[
            styles.emoji, 
            styles.ball, 
            { 
              transform: [
                { translateX: flyInterpolateX },
                { translateY: flyInterpolateY },
                { scale: flyAnim.interpolate({
                  inputRange: [0, 0.4, 0.5, 1],
                  outputRange: [1, 0.6, 0.5, 1]
                }) }
              ],
              opacity: flyOpacity
            }
          ]}
        >
          🎾
        </Animated.Text>
      </View>
      <Text style={styles.loadingText}>Loading...</Text>
      <Text style={styles.factText}>{fact}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f172a',
    padding: 20
  },
  animationContainer: {
    width: 200,
    height: 150,
    position: 'relative',
    marginBottom: 20
  },
  emoji: {
    position: 'absolute',
  },
  player: {
    fontSize: 60,
    left: 20,
    bottom: 0,
  },
  racket: {
    fontSize: 45,
    left: 70,
    bottom: 25,
  },
  ball: {
    fontSize: 30,
    left: 90,
    bottom: 40,
  },
  loadingText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#38bdf8',
    marginBottom: 15
  },
  factText: {
    fontSize: 16,
    color: '#cbd5e1',
    textAlign: 'center',
    lineHeight: 24,
    maxWidth: 300
  }
});
