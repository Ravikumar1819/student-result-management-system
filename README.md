# Student Result Management System

Role-based student and examination management with automatic grades and result reports.

This is a fresh implementation based on the project description in Ravi Kumar's resume. It does not claim to recover an earlier codebase or demonstrate past production usage.

## Run locally

Requires Python 3.11+. From this repository:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m flask --app app run --port 5000
```

Open http://localhost:5000. Set configuration as environment variables; `.env.example` documents the available values. Flask does not automatically load `.env` unless python-dotenv is installed. For persistent sessions set SECRET_KEY to a random secret. SQLite data is created automatically in `instance/app.db`. To reset local data, stop the server and remove that database.

## Verify

```sh
python -m pytest -q
python -m ruff check .
```

## Docker

```sh
docker build -t student-result-management-system .
docker run --rm -p 5000:5000 -e SECRET_KEY=your-random-secret -v student-result-management-system-data:/app/instance student-result-management-system
```

The image serves with Waitress as a non-root user. Check volume ownership if using a host directory. `/api/health` returns a health check. Never commit `.env`, database files or credentials.

## Deployment boundaries

This is a portfolio application. Before public deployment, use HTTPS, set COOKIE_SECURE=true for cookie apps, configure a persistent database and SECRET_KEY, add authentication rate limiting, monitoring and backups, and review access rules. No default account or password is shipped. CI is configured to run lint and tests on pushes and pull requests.

## Accounts and workflow

Create the first administrator explicitly (the command securely prompts for a password):

```sh
python -m flask --app app create-admin admin
```

Students self-register from the sign-in form. An administrator creates a student record and links it to that account. Students can view only their linked records; administrators can create, edit and delete students, exams and marks. Removing a student or exam cascades to its results. Use the print button to generate a report with your browser. Grade thresholds are documented in the UI and tested at boundaries.

Session cookies are HTTP-only with SameSite=Lax. Every mutation requires a session-bound CSRF token. Passwords use Werkzeug scrypt hashes. Public registration cannot grant administrator rights. API: GET /api/session, POST /api/register, POST /api/login, POST /api/logout, GET /api/records, POST/PUT/DELETE /api/students[/id], POST/PUT/DELETE /api/exams[/id], PUT /api/results, DELETE /api/results/student_id/exam_id. JSON errors use an `error` field.
