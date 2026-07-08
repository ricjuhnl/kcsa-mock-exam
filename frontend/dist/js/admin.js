const ADMIN_USER = '';
const ADMIN_PASS = '';

class AdminPanel {
    constructor() {
        this.questions = [];
        this.sessions = [];
        this.stats = {};
    }

    async init() {
        await Promise.all([
            this.loadQuestions(),
            this.loadSessions(),
            this.loadStats()
        ]);
    }

    async callApi(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + btoa(ADMIN_USER + ':' + ADMIN_PASS)
        };

        const response = await fetch(`${endpoint}`, {
            ...options,
            headers: { ...headers, ...options.headers }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        return response.json();
    }

    async loadQuestions() {
        try {
            this.questions = await this.callApi('/api/admin/questions');
            this.renderQuestions();
        } catch (error) {
            console.error('Failed to load questions:', error);
            alert('Failed to load questions. Check console for details.');
        }
    }

    renderQuestions() {
        const tbody = document.getElementById('questions-tbody');
        tbody.innerHTML = '';

        this.questions.forEach(q => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${q.id}</td>
                <td>${q.domain.substring(0, 40)}...</td>
                <td>${q.question_text.substring(0, 50)}...</td>
                <td>
                    <button class="action-btn edit-btn" onclick="adminPanel.editQuestion(${q.id})">Edit</button>
                    <button class="action-btn delete-btn" onclick="adminPanel.deleteQuestion(${q.id})">Delete</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async loadSessions() {
        try {
            this.sessions = await this.callApi('/api/admin/sessions');
            this.renderSessions();
        } catch (error) {
            console.error('Failed to load sessions:', error);
        }
    }

    renderSessions() {
        const tbody = document.getElementById('sessions-tbody');
        tbody.innerHTML = '';

        this.sessions.forEach(s => {
            const row = document.createElement('tr');
            const score = s.score ? `${s.score}%` : '-';
            const result = s.passed ?
                '<span style="color: var(--success-color);">PASSED</span>' :
                (s.passed === false ? '<span style="color: var(--error-color);">FAILED</span>' : '-');

            row.innerHTML = `
                <td>${s.id.substring(0, 12)}...</td>
                <td>${new Date(s.created_at).toLocaleString()}</td>
                <td>${score}</td>
                <td>${result}</td>
            `;
            tbody.appendChild(row);
        });
    }

    async loadStats() {
        try {
            this.stats = await this.callApi('/api/admin/stats');
            this.renderStats();
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    renderStats() {
        const cardsContainer = document.getElementById('stats-cards');
        cardsContainer.innerHTML = `
            <div class="stats-card">
                <h3>Total Sessions</h3>
                <div class="value">${this.stats.totalSessions || 0}</div>
            </div>
            <div class="stats-card">
                <h3>Total Questions</h3>
                <div class="value">${this.stats.totalQuestions || 0}</div>
            </div>
            <div class="stats-card">
                <h3>Average Score</h3>
                <div class="value">${this.stats.averageScore || 0}%</div>
            </div>
            <div class="stats-card">
                <h3>Pass Rate</h3>
                <div class="value">${this.stats.passRate || 0}%</div>
            </div>
        `;

        const tbody = document.getElementById('domain-stats-tbody');
        tbody.innerHTML = '';

        for (const [domain, stats] of Object.entries(this.stats.domainBreakdown || {})) {
            tbody.innerHTML += `
                <tr>
                    <td>${domain}</td>
                    <td>${stats.total}</td>
                    <td>${stats.correct}</td>
                    <td><strong>${stats.percentage}%</strong></td>
                </tr>
            `;
        }
    }

    showSection(section) {
        document.getElementById('questions-section').style.display = section === 'questions' ? 'block' : 'none';
        document.getElementById('sessions-section').style.display = section === 'sessions' ? 'block' : 'none';
        document.getElementById('stats-section').style.display = section === 'stats' ? 'block' : 'none';
    }

    showAddQuestion() {
        document.getElementById('modal-title').innerText = 'Add Question';
        document.getElementById('edit-question-id').value = '';
        document.getElementById('question-form').reset();
        document.getElementById('question-modal').style.display = 'block';
    }

    editQuestion(questionId) {
        const question = this.questions.find(q => q.id === questionId);
        if (!question) return;

        document.getElementById('modal-title').innerText = 'Edit Question';
        document.getElementById('edit-question-id').value = questionId;
        document.getElementById('question-domain').value = question.domain;
        document.getElementById('question-text').value = question.question_text;
        document.getElementById('question-code').value = question.code || '';
        document.getElementById('question-explanation').value = question.explanation;

        const options = JSON.parse(question.options);
        document.getElementById('option-0').value = options[0];
        document.getElementById('option-1').value = options[1];
        document.getElementById('option-2').value = options[2];
        document.getElementById('option-3').value = options[3];

        const answerSelect = document.getElementById('correct-answer');
        answerSelect.innerHTML = '';
        options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt;
            option.text = opt;
            if (opt === question.correct_answer) option.selected = true;
            answerSelect.appendChild(option);
        });

        document.getElementById('question-modal').style.display = 'block';
    }

    async saveQuestion(event) {
        event.preventDefault();

        const questionId = document.getElementById('edit-question-id').value;
        const domain = document.getElementById('question-domain').value;
        const questionText = document.getElementById('question-text').value;
        const code = document.getElementById('question-code').value || null;
        const options = [
            document.getElementById('option-0').value,
            document.getElementById('option-1').value,
            document.getElementById('option-2').value,
            document.getElementById('option-3').value
        ];
        const correctAnswer = document.getElementById('correct-answer').value;
        const explanation = document.getElementById('question-explanation').value;

        const data = {
            domain,
            question_text: questionText,
            code,
            options,
            correct_answer: correctAnswer,
            explanation
        };

        try {
            if (questionId) {
                await this.callApi(`/api/admin/questions/${questionId}`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
            } else {
                await this.callApi('/api/admin/questions', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
            }

            this.closeModal();
            await this.loadQuestions();
            alert('Question saved successfully!');
        } catch (error) {
            console.error('Failed to save question:', error);
            alert('Failed to save question. Check console for details.');
        }
    }

    async deleteQuestion(questionId) {
        if (!confirm('Are you sure you want to delete this question?')) return;

        try {
            await this.callApi(`/api/admin/questions/${questionId}`, {
                method: 'DELETE'
            });
            await this.loadQuestions();
            alert('Question deleted successfully!');
        } catch (error) {
            console.error('Failed to delete question:', error);
            alert('Failed to delete question. Check console for details.');
        }
    }

    closeModal() {
        document.getElementById('question-modal').style.display = 'none';
    }
}

window.AdminPanel = AdminPanel;

document.getElementById('question-form').addEventListener('submit', (e) => {
    adminPanel.saveQuestion(e);
});

document.getElementById('question-domain').addEventListener('change', function() {
    document.getElementById('question-text').value = '';
    document.getElementById('question-code').value = '';
    for (let i = 0; i < 4; i++) {
        document.getElementById(`option-${i}`).value = '';
    }
    document.getElementById('correct-answer').innerHTML = '';
    document.getElementById('question-explanation').value = '';
});

document.querySelectorAll('#option-0, #option-1, #option-2, #option-3').forEach(input => {
    input.addEventListener('input', function() {
        const answerSelect = document.getElementById('correct-answer');
        answerSelect.innerHTML = '';
        for (let i = 0; i < 4; i++) {
            const val = document.getElementById(`option-${i}`).value;
            if (val) {
                const option = document.createElement('option');
                option.value = val;
                option.text = val;
                answerSelect.appendChild(option);
            }
        }
    });
});
