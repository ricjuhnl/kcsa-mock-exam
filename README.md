# KCSA Mock Exam Simulator

A Dockerized mock exam tool for the Kubernetes and Cloud Associate (KCSA) certification. Features 100+ questions covering all KCSA exam domains with randomized 60-question sessions.

## Features

- **60-question randomized exams** based on official KCSA blueprint proportions
- **100+ questions** across 6 exam domains
- **Session-based tracking** with persistent results (auto-cleanup after 7 days)
- **Admin panel** for question management and analytics
- **Domain-based scoring** with performance breakdown
- **90-minute timer** matching official exam conditions
- **Docker Compose** deployment - runs anywhere

## Quick Start

### Prerequisites

- Docker and Docker Compose installed

### Deploy

```bash
# Clone the repository
git clone https://github.com/ricjuhnl/kcsa-mock-exam.git
cd kcsa-mock-exam

# Start the services
docker compose up -d

# Open in browser
open http://localhost:80
```

### Admin Panel

Access the admin panel at `http://localhost:80/admin.html`

- **Username:** `kcsa_admin`
- **Password:** `change_me_in_production`

Change the default credentials in `.env` before production use.

## Project Structure

```
kcsa-exam/
├── docker-compose.yml      # Docker Compose configuration
├── .env                    # Environment variables (admin credentials)
├── .htpasswd               # Nginx basic auth (auto-generated)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py         # FastAPI backend + API routes
│       ├── database.py     # SQLite database setup
│       ├── models.py       # Pydantic models
│       └── seed.py         # Question extraction from source
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf          # Nginx configuration
│   └── dist/
│       ├── index.html      # Exam interface
│       ├── admin.html      # Admin panel
│       ├── css/style.css   # Styles
│       └── js/
│           ├── api.js      # API client
│           ├── exam.js     # Quiz engine
│           └── admin.js    # Admin panel logic
└── data/                   # SQLite database (persistent volume)
    └── exams.db
```

## API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/questions` | Get 60 randomized questions |
| POST | `/api/sessions` | Create new exam session |
| POST | `/api/sessions/{id}/submit` | Submit exam answers |
| GET | `/api/sessions/{id}` | Get session results |

### Admin Endpoints (Basic Auth Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/questions` | List all questions |
| POST | `/api/admin/questions` | Add a new question |
| PUT | `/api/admin/questions/{id}` | Update a question |
| DELETE | `/api/admin/questions/{id}` | Delete a question |
| GET | `/api/admin/sessions` | List all exam sessions |
| GET | `/api/admin/stats` | Aggregate statistics |

## Exam Domains

Questions are distributed according to the official KCSA blueprint:

| Domain | Weight | Questions per Exam |
|--------|--------|-------------------|
| Overview of Cloud Native Security | 14% | 8 |
| Kubernetes Cluster Component Security | 22% | 13 |
| Kubernetes Security Fundamentals | 22% | 13 |
| Kubernetes Threat Model | 16% | 10 |
| Platform Security | 16% | 10 |
| Compliance and Security Frameworks | 10% | 6 |

## Deployment

### Local / VM

```bash
docker compose up -d
```

### Production

1. Update `.env` with secure admin credentials
2. Regenerate `.htpasswd`:
   ```bash
   ./generate_htpasswd.sh <username> <password>
   ```
3. Deploy:
   ```bash
   docker compose up -d
   ```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_USER` | `kcsa_admin` | Admin panel username |
| `ADMIN_PASS` | `change_me_in_production` | Admin panel password |

## Development

### Add New Questions

1. Add questions to the database via the admin panel or API
2. Questions are stored in SQLite (`data/exams.db`)
3. Each session randomly selects 60 questions based on the blueprint

### Rebuild

```bash
docker compose build --no-cache
docker compose up -d
```

## License

MIT
