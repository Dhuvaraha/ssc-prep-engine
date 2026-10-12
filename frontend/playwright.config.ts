import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: {
    baseURL: "http://localhost:4173",
    channel: process.platform === "win32" ? "msedge" : undefined,
    headless: true,
    trace: "off",
  },
  webServer: [
    {
      command: process.platform === "win32"
        ? "..\\backend\\.venv\\Scripts\\python -m uvicorn phase_a_browser_app:app --app-dir ../backend/tests --host 127.0.0.1 --port 8811"
        : "python -m uvicorn phase_a_browser_app:app --app-dir ../backend/tests --host 127.0.0.1 --port 8811",
      env: { PYTHONPATH: "../backend", DATABASE_URL: "sqlite://", CORS_ORIGINS: "http://localhost:4173", JWT_SECRET: "synthetic-browser-tests-only" },
      url: "http://127.0.0.1:8811/health",
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 4173",
      env: { VITE_API_BASE_URL: "http://127.0.0.1:8811/api/v1" },
      url: "http://localhost:4173",
      reuseExistingServer: false,
    },
  ],
});
