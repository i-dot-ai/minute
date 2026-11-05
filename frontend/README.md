# Minute Frontend

### Development

For the full application, follow the [local Compose setup](../README.md#run-the-app-locally).
It serves the frontend at http://localhost:3000 and does not require a host Node.js installation.

To run only the frontend on the host, install Node.js 24+, then run from `frontend/`:

```sh
npm ci
npm run dev
```

Use the full stack for real API requests. For browser tests with a mocked backend, run
`npm run test:e2e:mocked` after installing Playwright browsers with `npx playwright install`.
