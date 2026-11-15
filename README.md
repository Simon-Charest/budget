# Budget

A private, English/French household-budget web app built with Python, FastAPI, and SQLite. The app focuses on expenses imported from the **Brut** (Budget) sheet. The workbook's Transfers and Salary sheets are intentionally not included yet; additional reporting, such as who owns what and who owes whom, can be added later.

## What it does

- Requires sign-in before displaying any budget data or serving budget APIs.
- Stores dated expenses in an encrypted local SQLite database. An Excel workbook can be used for an initial import.
- Shows expense totals, averages, category and monthly summaries, and a searchable, paginated transaction table.
- Filters transactions by year, category, and payer.
- Includes an administrator-only Users page to create and remove accounts.
- Provides English and French UI text, icon buttons, a custom favicon, a top navigation bar, and a footer.

The import includes date, amount, type/category, supplier, description, payer, transfer recipient, and comments. It accepts both numeric spreadsheet amounts and common comma/dot-formatted amounts. After import, the database is the source of truth; the workbook is not needed to run the app. User accounts and sessions are kept in SQLite.

## Requirements

- Python 3.10 or later
- An existing encrypted database, or an Excel workbook for the initial import

## Configure with `.env`

Create a private `.env` in the project root using the settings below. `.env.example` is intentionally empty because environment-specific settings belong only in the ignored `.env` file. Set `BUDGET_DATABASE_PASSWORD` to a unique secret of at least 16 characters before starting the app. Do not commit `.env` or share the password. The app reads it on startup, and real process environment variables take precedence.

| Setting | Default | Description |
| --- | --- | --- |
| `BUDGET_DATABASE` | `data/budget.sqlite3` | SQLite database path; relative paths are resolved from the project directory. |
| `BUDGET_DATABASE_PASSWORD` | *(required)* | SQLCipher encryption password, at least 16 characters. Set a long, unique password before first startup and keep a secure copy; without it the app cannot open the database. |
| `BUDGET_HOST` | `localhost` | Address Uvicorn listens on. Keep localhost when using Nginx. |
| `BUDGET_PORT` | `80` | Uvicorn listening port. |
| `BUDGET_COOKIE_SECURE` | `false` | Set to `true` when the public site uses HTTPS. |
| `BUDGET_SESSION_HOURS` | `12` | Sign-in session lifetime. |
| `BUDGET_PROXY_HEADERS` | `true` | Honor proxy headers from the configured trusted proxy. |
| `BUDGET_FORWARDED_ALLOW_IPS` | `localhost` | Trusted proxy IPs for Uvicorn; do not use `*` on a public server. |
| `BUDGET_LOG_LEVEL` | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. |
| `BUDGET_DEPLOY_REMOTE` | `scharest@NUC7i3BNH` | SSH account and host used by `bin/deploy.ps1`. |
| `BUDGET_DEPLOY_REMOTE_ROOT` | `~/source/budget` | Remote project checkout. The deploy script resolves `~` using the SSH user's home directory. |
| `BUDGET_DEPLOY_BRANCH` | `main` | Git branch pushed to GitHub and pulled on the Ubuntu machine. |

The `.env` file format is compatible with the included systemd `EnvironmentFile`. The systemd unit and Nginx site are infrastructure configuration, so they remain in `deploy/`; the app's runtime settings and deployment target are in `.env`.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Create .env using the settings above before running the app.
python . create-admin
python .
```

On Windows, activate the environment with `.venv\Scripts\Activate.ps1` and create `.env` using the settings above. The included `bin/run.ps1` starts the local app on `http://127.0.0.1:80`; running `python .` directly uses the `BUDGET_HOST` and `BUDGET_PORT` in `.env`.

The first administrator is created by the interactive `create-admin` command. It asks for an email, first and last name, and a password twice. The password is entered at a hidden prompt, never as a command-line argument. Administrators can create other accounts from the Users page; self-service registration is disabled.

## Deploy to Ubuntu

Use the provided `deploy/budget.service` and `deploy/budget.nginx`. Production Uvicorn listens only on `127.0.0.1:8000`; Nginx accepts public traffic on port 80/443 and proxies to it. Do not expose port 8000 directly to the internet.

1. On the Ubuntu machine, use the SSH account named in `BUDGET_DEPLOY_REMOTE`. Clone this repository to the location in `BUDGET_DEPLOY_REMOTE_ROOT` (the deploy script supports `~/...` paths). Create a Python virtual environment there and install `requirements.txt`. Keep the checkout owned by that SSH account.
2. Set `BUDGET_DATABASE_PASSWORD` in the local `.env` to a unique secret of at least 16 characters. The deploy script sends a production copy of `.env` over SSH, preserving that password while setting server paths and security options. Do not commit `.env`.
3. Configure the Ubuntu service account and sudo access. The provided systemd unit runs as the SSH user and uses their checkout. The deploy account must be able to run the script's `sudo install` and `sudo systemctl` commands; interactive sudo may prompt during deployment.
4. The deploy script creates the production configuration with:

   ```dotenv
   BUDGET_DATABASE=~/source/budget/data/budget.sqlite3
   BUDGET_HOST=127.0.0.1
   BUDGET_PORT=8000
   BUDGET_COOKIE_SECURE=true
   BUDGET_PROXY_HEADERS=true
   BUDGET_FORWARDED_ALLOW_IPS=127.0.0.1
   ```

5. Before the first deploy, create the initial administrator on the server: `cd ~/source/budget && .venv/bin/python . create-admin`.
6. On the Ubuntu machine, install `deploy/budget.nginx` as an Nginx site for `budget.slcti.ca`, enable it, then configure HTTPS with Certbot: `sudo certbot --nginx -d budget.slcti.ca`.
7. On Windows, run `.\bin\deploy.ps1`. It stages and commits source files, pushes the configured Git branch to GitHub, securely transfers `.env`, pulls the pushed commit on the server, installs/restarts the systemd service, creates and verifies an encrypted production database backup, downloads it, backs up the old local database, and replaces the local database with the production copy. Stop the local app before deploying; the script checks the local port and refuses to overwrite a running database.

The deployment script requires SSH key access, a pre-existing remote Git checkout and virtual environment, and working GitHub authentication. The remote username, checkout path, and branch are read from `.env`. Remote and local encrypted database snapshots are retained in `data/backups`; prune old snapshots periodically. The script synchronizes local development data from production on every successful deployment, so local changes to the database are replaced (an encrypted pre-sync backup is kept).

The provided systemd service binds Uvicorn only to localhost, trusts forwarded headers only from localhost, runs one worker, and limits writes to the checkout's data directory.

## Security

- The SQLite database is encrypted at rest with SQLCipher. `BUDGET_DATABASE_PASSWORD` is required to open it. Losing the password means losing access to the database; it cannot be reset. Store it separately in a secure password manager.
- Passwords use salted scrypt hashes; session tokens are random and only stored as hashes.
- Session cookies are `HttpOnly`, `SameSite=Strict`, and expire. Enable `BUDGET_COOKIE_SECURE` for HTTPS.
- Login and account-management changes reject cross-origin requests. Security headers help prevent framing and content-type sniffing.
- Only an administrator can list, create, or remove accounts. Users cannot remove their own account, and the final administrator cannot be deleted.
- The database contains private financial information. Restrict filesystem access and protect encrypted database backups. On first startup with an existing plaintext SQLite file, the app encrypts it in place after creating and verifying an encrypted snapshot; the original is replaced, and no plaintext backup is retained.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```