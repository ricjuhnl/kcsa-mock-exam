const API_BASE = '';

export async function fetchQuestions() {
    const response = await fetch(`${API_BASE}/api/questions`);
    if (!response.ok) {
        throw new Error(`Failed to fetch questions: ${response.statusText}`);
    }
    const data = await response.json();
    return data.questions;
}

export async function createSession() {
    const response = await fetch(`${API_BASE}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    if (!response.ok) {
        throw new Error(`Failed to create session: ${response.statusText}`);
    }
    const data = await response.json();
    return data.sessionId;
}

export async function submitSession(sessionId, answers) {
    const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers })
    });
    if (!response.ok) {
        throw new Error(`Failed to submit session: ${response.statusText}`);
    }
    const data = await response.json();
    return data;
}

export async function getSessionResults(sessionId) {
    const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
    if (!response.ok) {
        throw new Error(`Failed to get session: ${response.statusText}`);
    }
    return await response.json();
}
