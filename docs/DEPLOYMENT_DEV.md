# Development CI/CD Deployment

Every successful push to `dev` runs backend tests and the frontend build, then
deploys one Docker Compose instance to the development server.

## Deployment target

- Server: `178.104.123.31`
- SSH user: `emmanuel`
- Suggested path: `/home/emmanuel/apps/flyingfoods-dev`
- Application URL: `http://178.104.123.31:8080`

## 1. Prepare the server once

Install Docker Engine with the Compose plugin, then ensure `emmanuel` can run
Docker without `sudo`.

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker emmanuel
```

Log out and back in after changing the Docker group. Then prepare the
deployment directory:

```bash
mkdir -p /home/emmanuel/apps/flyingfoods-dev
cd /home/emmanuel/apps/flyingfoods-dev
```

Copy `.env.dev.example` to `.env.dev` and replace every placeholder. The
PostgreSQL password in `POSTGRES_PASSWORD` and `DATABASE_URL` must match.
Keep `DJANGO_COOKIE_SECURE=False` only while this development instance is
served over plain HTTP. Set it to `True` when HTTPS is configured.

The development instance uses port `8080` because the server's existing Nginx
service already owns port `80`.

Do not commit `.env.dev`; the workflow deliberately preserves the server copy
during each upload.

## 2. Create a deployment SSH key

Create a dedicated key locally:

```powershell
ssh-keygen -t ed25519 -C "flyingfoods-github-actions" -f $HOME\.ssh\flyingfoods_dev_deploy
```

Install its public key on the server:

```powershell
Get-Content $HOME\.ssh\flyingfoods_dev_deploy.pub |
  ssh emmanuel@178.104.123.31 "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"
```

Verify key-only login:

```powershell
ssh -i $HOME\.ssh\flyingfoods_dev_deploy emmanuel@178.104.123.31
```

## 3. Add GitHub environment secrets

In GitHub, create the `development` environment and add:

| Secret | Value |
|---|---|
| `DEV_SSH_HOST` | `178.104.123.31` |
| `DEV_SSH_USER` | `emmanuel` |
| `DEV_DEPLOY_PATH` | `/home/emmanuel/apps/flyingfoods-dev` |
| `DEV_SSH_PRIVATE_KEY` | Full contents of `flyingfoods_dev_deploy` |
| `DEV_SSH_KNOWN_HOSTS` | Output of `ssh-keyscan -H 178.104.123.31` |

The private key must include its `BEGIN OPENSSH PRIVATE KEY` and `END OPENSSH
PRIVATE KEY` lines.

Add an environment variable named `DEV_DEPLOY_ENABLED` with value `true` only
after the server, `.env.dev`, SSH key, and secrets are ready. Until then, CI
still runs on `dev`, but the deployment job is safely skipped.

## 4. First deployment

Push a commit to `dev`, or manually re-run the latest workflow. GitHub Actions
will:

1. run the backend tests;
2. build the React frontend;
3. synchronize the release to the server;
4. build the Docker images;
5. apply Django migrations and collect static files;
6. restart the backend, worker, beat, and Nginx frontend.

## Operations

On the server:

```bash
cd /home/emmanuel/apps/flyingfoods-dev
docker compose --env-file .env.dev -f docker-compose.deploy.yml ps
docker compose --env-file .env.dev -f docker-compose.deploy.yml logs -f --tail=200
```

To seed demonstration users once:

```bash
docker compose --env-file .env.dev -f docker-compose.deploy.yml exec backend python manage.py seed_demo
```

Database and media data live in named Docker volumes and are not deleted by
normal deployments.
