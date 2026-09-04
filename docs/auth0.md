# Auth0 login and per-user BET storage

The application supports Streamlit's native OpenID Connect login with Auth0. Passwords, client secrets, access tokens, and ID tokens are not written to the BET data directory. Only the validated Auth0 `sub` claim is hashed to select an isolated storage directory.

## Auth0 application

Create an Auth0 **Regular Web Application** and configure these exact production URLs:

- Allowed Callback URL: `https://ai-baseball-studio.f-polaris.jp/oauth2callback`
- Allowed Logout URL: `https://ai-baseball-studio.f-polaris.jp/`
- Allowed Web Origin: `https://ai-baseball-studio.f-polaris.jp`

Do not use a wildcard callback URL in production.

## Server secret file

Copy `.streamlit/secrets.toml.example` to this production-only path:

`/opt/hawks-ai/auth0/secrets.toml`

Set restrictive permissions and replace all placeholders with the Auth0 domain, client ID, client secret, and a long random cookie secret. Never commit the populated file. The production deployment mounts it read-only into the container and enables Auth0 automatically.

Alternatively, configure all four GitHub Actions repository secrets below. The production workflow validates them, creates the TOML file without logging its values, uploads it with mode `0600`, and activates Auth0 during the same deployment.

- `AUTH0_DOMAIN`
- `AUTH0_CLIENT_ID`
- `AUTH0_CLIENT_SECRET`
- `AUTH0_COOKIE_SECRET` (at least 32 characters)

When this file is absent, the app retains the existing single-user BET file so deployments do not lock out the current operator. When present, login is mandatory and each account uses:

`/app/data/users/<sha256-of-auth0-sub>/bet_records.json`

The original `/app/data/bet_records.json` is retained and is not exposed to authenticated accounts. Export it before activation or migrate it to the intended user's directory after that user's first login.

Preview a server-side migration using the exact Auth0 `user_id`/`sub` from the Auth0 dashboard:

```bash
python scripts/migrate_legacy_bets.py --auth0-sub 'auth0|verified-user-id'
```

After checking the target and count, add `--apply`. If the target account already has records, the command refuses to overwrite them; use `--merge` to add only IDs that are not already present. The source legacy file is never removed.

## Verification

1. Open the production URL in a private window and confirm the Auth0 button appears.
2. Log in as user A, add one BET, and export the Excel workbook.
3. Log out, log in as user B, and confirm user A's BET is not visible.
4. Import the workbook for user B and confirm the server reports the validated row count.
5. Repeat the same import in append mode and confirm duplicate IDs are skipped.
