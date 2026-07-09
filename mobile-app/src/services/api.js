// API HTTP Service
const API_BASE_URL = 'https://tourney-pro-xi.vercel.app/api/v1';

export const loginUser = async (username, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    return response.json();
};

export const fetchTournaments = async () => {
    const response = await fetch(`${API_BASE_URL}/tournaments`);
    return response.json();
};

export const fetchMatches = async (categoryId) => {
    const response = await fetch(`${API_BASE_URL}/matches/category/${categoryId}`);
    return response.json();
};

export const reportMatch = async (matchId, actionType, status, score1, score2, winnerId, token) => {
    const response = await fetch(`${API_BASE_URL}/matches/${matchId}/report`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            action_type: actionType,
            match_status: status,
            score1,
            score2,
            winner_id: winnerId
        })
    });
    return response.json();
};
