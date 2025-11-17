# Load-balanced deployment with a dedicated worker app

You can run the UI/API in one Heroku app ("primary") and offload all torrent/Mega processing to a second Heroku app ("worker"). The worker uses the same codebase but only runs the `worker` process from the `Procfile`.

## Option A: share the database (recommended)
Sharing the Postgres database keeps things simple—no extra API work is required because the primary app reads torrent state directly from the database that the worker updates.

1. **Create/identify the primary app** – keep the existing app running both `web` and `worker` until the cutover.
2. **Create the worker app** – `heroku create your-worker-app`.
3. **Attach the same Postgres database** – `heroku addons:attach <PRIMARY_APP>::DATABASE -a your-worker-app` so both apps read/write the same data.
4. **Copy config vars** – copy all required env vars (Drive, TMDB, Genie, etc.) from the primary app to the worker. The critical one is `DATABASE_URL` from the attached database. Ensure `WORKER_API_TOKEN` is identical on both apps (used if you later add API callbacks).
5. **Scale processes** – on the primary app, scale the worker down (`heroku ps:scale worker=0 -a <PRIMARY_APP>`) if you want only the remote worker to process jobs. On the worker app, scale `worker=1` and `web=0` (`heroku ps:scale worker=1 web=0 -a your-worker-app`).
6. **Deploy the same code** – push the current branch to both apps (`git push heroku main` for the primary, `git push https://git.heroku.com/your-worker-app.git main` for the worker) so migrations and code match.
7. **Verify processing** – trigger a torrent/Mega job from the UI; it should be processed by the worker app while the primary app reflects progress via the shared database.

## Option B: API-bridged worker (separate databases)
If you prefer database isolation, you can let the worker post progress back to the primary API. This requires enabling a shared secret on both apps and pointing the worker to the primary’s API URL.

1. Set `PRIMARY_API_BASE` on the worker app to your primary app’s URL (e.g., `https://your-primary-app.herokuapp.com`).
2. Set the same `WORKER_API_TOKEN` on both apps. The worker includes this token in API calls; the primary validates it before accepting status updates.
3. Run the worker app with `worker=1` and `web=0`; the primary runs `web=1` (and `worker=0` if you want the worker-only model).
4. Implement or enable the minimal status endpoints on the primary (`/api/worker/update`) that authenticate with `WORKER_API_TOKEN` so the worker can send state changes when torrents or Mega downloads advance.

## Operational notes
- Keep code and migrations in sync across both apps; mismatched schemas will break processing.
- Monitor logs separately (`heroku logs -t -a your-worker-app` and `heroku logs -t -a your-primary-app`).
- If you later need to rotate secrets, update `WORKER_API_TOKEN` on both apps and redeploy the worker.
