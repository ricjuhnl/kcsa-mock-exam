import { fetchQuestions, createSession, submitSession, getSessionResults } from '/js/api.js';

class ExamEngine {
    constructor() {
        this.sessionId = localStorage.getItem('exam_session_id');
        this.questions = [];
        this.currentQuestionIndex = 0;
        this.userAnswers = [];
        this.stateSubmitted = [];
        this.totalSeconds = 90 * 60;
        this.timerInterval = null;
    }

    async init() {
        try {
            if (!this.sessionId) {
                this.sessionId = await createSession();
                localStorage.setItem('exam_session_id', this.sessionId);
            }

            this.questions = await fetchQuestions();
            this.userAnswers = new Array(this.questions.length).fill(null);
            this.stateSubmitted = new Array(this.questions.length).fill(false);

            document.getElementById('total-q-num').innerText = this.questions.length;
            this.showQuestion();
            this.startTimer();
        } catch (error) {
            console.error('Failed to initialize exam:', error);
            alert('Failed to load exam. Please refresh the page.');
        }
    }

    startTimer() {
        this.updateTimerDisplay();
        this.timerInterval = setInterval(() => {
            if (this.totalSeconds <= 0) {
                clearInterval(this.timerInterval);
                alert('Time has expired! Submitting your exam.');
                this.calculateResults();
                return;
            }
            this.totalSeconds--;
            this.updateTimerDisplay();
        }, 1000);
    }

    updateTimerDisplay() {
        const mins = Math.floor(this.totalSeconds / 60);
        const secs = this.totalSeconds % 60;
        document.getElementById('timer-display').innerText =
            `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    showQuestion() {
        const q = this.questions[this.currentQuestionIndex];
        document.getElementById('current-q-num').innerText = this.currentQuestionIndex + 1;

        let html = `
            <span class="domain-tag">${q.domain}</span>
            <div class="question-text">${this.currentQuestionIndex + 1}. ${q.question}</div>
        `;

        if (q.code) {
            html += `<pre><code>${this.escapeHtml(q.code)}</code></pre>`;
        }

        html += `<ul class="options-list">`;
        q.options.forEach((option, idx) => {
            const checked = this.userAnswers[this.currentQuestionIndex] === idx ? 'checked' : '';
            const disabled = this.stateSubmitted[this.currentQuestionIndex] ? 'disabled' : '';
            html += `
                <li class="option-item">
                    <label class="option-label">
                        <input type="radio" name="option" value="${idx}" ${checked} ${disabled}
                               onchange="examEngine.saveAnswer(${idx})">
                        <span>${this.escapeHtml(option)}</span>
                    </label>
                </li>
            `;
        });
        html += `</ul>`;
        html += `<div id="explanation" class="explanation-box"></div>`;

        document.getElementById('question-container').innerHTML = html;
        document.getElementById('prev-btn').disabled = this.currentQuestionIndex === 0;

        const actionBtn = document.getElementById('action-btn');
        if (this.stateSubmitted[this.currentQuestionIndex]) {
            this.showExplanationBox();
            actionBtn.innerText = (this.currentQuestionIndex === this.questions.length - 1) ? 'Finish Exam' : 'Next Question';
        } else {
            actionBtn.innerText = 'Submit Answer';
        }
    }

    saveAnswer(optionIndex) {
        this.userAnswers[this.currentQuestionIndex] = optionIndex;
    }

    handleActionClick() {
        if (!this.stateSubmitted[this.currentQuestionIndex]) {
            const selectedOpt = document.querySelector('input[name="option"]:checked');
            if (!selectedOpt) {
                alert('Please select an option before submitting.');
                return;
            }

            const answerIdx = parseInt(selectedOpt.value);
            this.userAnswers[this.currentQuestionIndex] = answerIdx;
            this.stateSubmitted[this.currentQuestionIndex] = true;

            this.showExplanationBox();

            const actionBtn = document.getElementById('action-btn');
            actionBtn.innerText = (this.currentQuestionIndex === this.questions.length - 1) ? 'Finish Exam' : 'Next Question';
            this.showQuestion();
        } else {
            if (this.currentQuestionIndex === this.questions.length - 1) {
                this.submitExam();
            } else {
                this.currentQuestionIndex++;
                this.showQuestion();
            }
        }
    }

    prevQuestion() {
        if (this.currentQuestionIndex > 0) {
            this.currentQuestionIndex--;
            this.showQuestion();
        }
    }

    showExplanationBox() {
        const q = this.questions[this.currentQuestionIndex];
        const selectedIdx = this.userAnswers[this.currentQuestionIndex];
        const expBox = document.getElementById('explanation');

        if (!expBox || selectedIdx === null) return;

        const selectedAnswer = q.options[selectedIdx];
        const isCorrect = selectedAnswer === q.answer;

        if (isCorrect) {
            expBox.className = 'explanation-box correct';
            expBox.innerHTML = `<strong>Correct!</strong> ${q.explanation}`;
        } else {
            expBox.className = 'explanation-box incorrect';
            expBox.innerHTML = `<strong>Incorrect.</strong> The correct choice was: <em>${this.escapeHtml(q.answer)}</em>.<br><br>${q.explanation}`;
        }
        expBox.style.display = 'block';
    }

    async submitExam() {
        try {
            const answers = {};
            this.questions.forEach((q, idx) => {
                if (this.userAnswers[idx] !== null) {
                    answers[q.id] = this.userAnswers[idx];
                }
            });

            const results = await submitSession(this.sessionId, answers);
            this.displayResults(results);
        } catch (error) {
            console.error('Failed to submit exam:', error);
            alert('Failed to submit exam. Please try again.');
        }
    }

    displayResults(results) {
        clearInterval(this.timerInterval);
        document.getElementById('quiz-screen').style.display = 'none';
        document.getElementById('results-screen').style.display = 'block';

        document.getElementById('final-score').innerText = `${results.score}%`;

        const statusEl = document.getElementById('pass-fail-status');
        if (results.passed) {
            statusEl.innerText = 'PASSED';
            statusEl.style.color = 'var(--success-color)';
        } else {
            statusEl.innerText = 'FAILED';
            statusEl.style.color = 'var(--error-color)';
        }

        const tbody = document.querySelector('#breakdown-table tbody');
        tbody.innerHTML = '';
        for (const [domain, stats] of Object.entries(results.domainBreakdown)) {
            tbody.innerHTML += `
                <tr>
                    <td>${domain}</td>
                    <td>${stats.correct} / ${stats.total}</td>
                    <td><strong>${stats.percentage}%</strong></td>
                </tr>
            `;
        }

        localStorage.removeItem('exam_session_id');
    }

    calculateResults() {
        let correctCount = 0;
        const domainStats = {};

        this.questions.forEach((q, idx) => {
            if (!domainStats[q.domain]) {
                domainStats[q.domain] = { correct: 0, total: 0 };
            }
            domainStats[q.domain].total++;

            if (this.userAnswers[idx] !== null) {
                const selectedAnswer = q.options[this.userAnswers[idx]];
                if (selectedAnswer === q.answer) {
                    correctCount++;
                    domainStats[q.domain].correct++;
                }
            }
        });

        const results = {
            sessionId: this.sessionId,
            totalQuestions: this.questions.length,
            correctAnswers: correctCount,
            score: Math.round((correctCount / this.questions.length) * 100),
            passed: (correctCount / this.questions.length) * 100 >= 75,
            domainBreakdown: {}
        };

        for (const [domain, stats] of Object.entries(domainStats)) {
            results.domainBreakdown[domain] = {
                correct: stats.correct,
                total: stats.total,
                percentage: Math.round((stats.correct / stats.total) * 100)
            };
        }

        this.displayResults(results);
    }

    escapeHtml(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    }
}

export { ExamEngine };
