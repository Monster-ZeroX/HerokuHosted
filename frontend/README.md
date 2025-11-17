# Torrent2Drive Next.js Frontend

A glassmorphic dashboard built with Next.js that speaks to the Flask API. Set `NEXT_PUBLIC_API_BASE` to your backend URL (e.g. the Heroku app) and run:

```bash
npm install
npm run dev
```

The app expects the Flask server to expose the JSON endpoints added under `/api/*` with session cookies enabled.
