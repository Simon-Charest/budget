# Budget

A private, multilingual household-budget web app built with Python, FastAPI, and SQLite. The app focuses on expenses and reporting.

## What it does

- Requires sign-in before displaying any budget data or serving budget APIs.
- Stores dated expenses in an encrypted local SQLite database.
- Shows expense totals, averages, category and monthly summaries, and a searchable, paginated transaction table.
- Defaults to the latest available month, with an option to view all months; transactions are shown in ascending date order.
- Filters each transaction column independently, sorts the budget by any data column in either direction, and supports adding, editing, and deleting expenses.
- Includes an administrator-only Categories page with filterable, sortable English and French names; administrators can add, edit, and delete unused categories. Editing a category to match both names of another category merges the categories and preserves their expenses.
- Keeps the navigation at the top and the footer at the bottom of the browser layout.
- Includes one administrator-only People list for both sign-in accounts and household members without login credentials. Email, account type, and password are only used for people who need access. Payers and recipients are selected from this same list.
- Provides multilingual UI text, icon buttons, a custom favicon, a top navigation bar, and a footer.

The data includes date, amount, category, merchant, description, payer, and recipient. Legacy comments are merged into the description with a semicolon. Midnight time suffixes (`00:00:00`) are removed from descriptions during import and entry. Dates are entered and shown as `yyyy-mm-dd`. Login accounts, household members without login access, translated categories, and sessions are kept in SQLite.

## Requirements

- Python 3.10 or later
- An existing encrypted database

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
| `BUDGET_DEPLOY_PASSWORD` | *(none)* | sudo password of the deploy account on the server, so `bin/deploy.ps1` asks no questions. Sent through SSH's input, never on a command line, and never copied to the server's `.env`. Leave it empty only if that account has passwordless sudo. |

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

Use the provided `deploy/budget.service` and `deploy/budget.nginx`. Production Uvicorn listens only on `127.0.0.1:8001` (port 8000 belongs to PyCharting on the same server). Nginx owns ports 80 and 443 for every site on the machine: a `stream` block in `/etc/nginx/streams-enabled/slcti.conf` routes port 443 by SNI name (`www.slcti.ca` to `:3000`, `pycharting.slcti.ca` to `:8443`, `budget.slcti.ca` to `:8444`), and `deploy/budget.nginx` terminates TLS on `127.0.0.1:8444` and proxies to the app. Do not expose port 8001 directly to the internet.

1. On the Ubuntu machine, use the SSH account named in `BUDGET_DEPLOY_REMOTE`. Clone this repository to the location in `BUDGET_DEPLOY_REMOTE_ROOT` (the deploy script supports `~/...` paths). Create a Python virtual environment there and install `requirements.txt`. Keep the checkout owned by that SSH account.
2. Set `BUDGET_DATABASE_PASSWORD` in the local `.env` to a unique secret of at least 16 characters. The deploy script sends a production copy of `.env` over SSH, preserving that password while setting server paths and security options. Do not commit `.env`.
3. Configure the Ubuntu service account and sudo access. The provided systemd unit runs as the SSH user and uses their checkout. The deploy account must be able to run `sudo install`, `sudo systemctl` and `sudo journalctl` for the `budget` unit; set its password in `BUDGET_DEPLOY_PASSWORD` (see above). The script checks sudo before committing anything.
4. The deploy script creates the production configuration with:

   ```dotenv
   BUDGET_DATABASE=~/source/budget/data/budget.sqlite3
   BUDGET_HOST=127.0.0.1
   BUDGET_PORT=8001
   BUDGET_COOKIE_SECURE=true
   BUDGET_PROXY_HEADERS=true
   BUDGET_FORWARDED_ALLOW_IPS=127.0.0.1
   ```

5. Before the first deploy, create the initial administrator on the server: `cd ~/source/budget && .venv/bin/python . create-admin`.
6. On the Ubuntu machine, issue the certificate with the webroot used by the shared port-80 site (`sudo certbot certonly --webroot -w /var/www/letsencrypt -d budget.slcti.ca`), add `budget.slcti.ca 127.0.0.1:8444;` to the stream map, copy `deploy/budget.nginx` to `/etc/nginx/sites-enabled/budget-ssl.conf`, then `sudo nginx -t && sudo systemctl reload nginx`. Do not use `certbot --nginx`: it would add a `listen 443` to the `http` block, which conflicts with the stream router and takes every site down. The deploy script never changes Nginx.
7. On Windows, run `.\bin\deploy.ps1`. It asks no questions. It stages and commits source files, pushes the configured Git branch to GitHub, securely transfers `.env`, pulls the pushed commit on the server, installs/restarts the systemd service, creates and verifies an encrypted production database backup, downloads it, backs up the old local database, and replaces the local database with the production copy. Stop the local app before deploying; the script checks the local port and refuses to overwrite a running database.

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

## License
- Distributed under the [MIT License](https://opensource.org/license/mit/). See [LICENSE.txt](./LICENSE.txt) for more information.

## Contact
- GitHub: [PyCharting](https://github.com/Simon-Charest/budget);
- Email: [Simon Charest](mailto:simoncharest@gmail.com).
