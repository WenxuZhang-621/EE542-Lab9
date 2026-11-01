# A: Public deployment handoff (2026-10-31)

Website: **https://desktop-jdferfe.taile24d30.ts.net/**

The website is published through Tailscale Funnel; visitors do not need Tailscale. It runs on A's Windows computer and goes offline if that computer shuts down, sleeps, loses connectivity, or stops its local services. It is not an independent always-on cloud server. Keep the device and tailnet names stable, especially after B completes domain association.

## Verified

- HTTPS with certificate and hostname validation; TLS verification was not skipped.
- Direct connections to public Funnel addresses obtained through public DNS-over-HTTPS, avoiding false positives from local Tailscale private DNS resolution.
- Registration/login for two accounts, with two WSS clients receiving the same messages and assistant loading/done events.
- Two real QA turns about Form 8843's purpose and the information it requests from students, using real OpenAI embeddings, C's index, local Llama, and MySQL.
- Matching source metadata after database readback; public-browser login, refresh, source display, and excerpt expansion.
- Registration without an invitation returns 403; unauthenticated chat-history access returns 401.
- `/.well-known/assetlinks.json` now returns JSON matching B's release package and certificate; HTTPS validation passed. **TWA behavior on the installed signed APK has not yet been verified.**
- 66 automated tests and five subtests passed. Evidence: `evidence/a/public-https-smoke.json`, `public-https-login.png`, and `public-https-sources.png`.

The verification script creates QA accounts/messages and makes two real RAG requests, using a small amount of embedding quota. Run it from the source directory with your own `.env`:

```powershell
python -m scripts.smoke_public --base-url https://desktop-jdferfe.taile24d30.ts.net
```

The script accepts only the exact local `PUBLIC_ORIGIN` to avoid sending the invitation code to another server. Read-only health endpoint: `/api/health`.

## Current deployment configuration

The officially signed Tailscale 1.104.4 client is installed and connected to a personal account. Windows IP Helper was changed from Disabled to Manual and started. That disabled prerequisite caused the initial 0x80070643 installation failure; installation succeeded after it was enabled.

Only `http://127.0.0.1:8000` is proxied, with TLS handled by Tailscale. Database port 13409 and model port 8001 remain local-only. The website uses one Uvicorn worker.

```powershell
& 'C:/Program Files/Tailscale/tailscale.exe' funnel --bg http://127.0.0.1:8000
& 'C:/Program Files/Tailscale/tailscale.exe' funnel status
```

These commands may require administrator privileges on this computer. The `--bg` Funnel configuration persists. After reboot, use the local `Start-Lab9.cmd` to start MySQL, the model, and the website; Funnel does not need to be enabled repeatedly.

To stop only this website's public forwarding:

```powershell
& 'C:/Program Files/Tailscale/tailscale.exe' funnel --https=443 off
```

Do not use `funnel reset`, which can remove configuration belonging to other apps. Re-run the earlier `funnel --bg` command to publish again. No other port forwarding was created.

## Team access and usage limits

The local `.env` sets `PUBLIC_MODE=true`, a random `REGISTRATION_CODE`, and the exact `PUBLIC_ORIGIN`. A shares the invitation privately with teammates; it is excluded from Git, source packages, logs, and public frontend configuration. New accounts need it; existing accounts do not need it for login.

Public mode allows 60 authentication requests/minute globally and 10/username; 120 messages/minute globally and 30/account; six assistant requests/minute/account and 60/hour globally; and one concurrent assistant request. Retries count toward limits. Rejected requests return 429 before chat persistence or model calls, and the page retains the draft.

Limits live in one process's memory and reset when the website restarts. This suits the single-computer group demonstration. Multiple workers or servers would require shared rate-limit state; do not scale simply by adding workers. Rotating the invitation affects new registrations only. Authenticated users share the chat room, whose history includes development QA messages and historical failures.

## Handoff to B

B sets `defaultUrl` to `https://desktop-jdferfe.taile24d30.ts.net/` and registers with the private invitation code. B returns the actual `applicationId` and the SHA-256 fingerprint of the certificate signing the installed APK. A generates and deploys Asset Links with `scripts.assetlinks`, then A/B jointly verify TWA launch without an address bar.

See `A-TO-B.md`. Public deployment alone does not establish completion of the Android APK, Part 5 custom embeddings, team phone recordings, GitHub submissions, or final PDF.
