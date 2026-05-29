/** @type {import('next').NextConfig} */
const nextConfig = {
  // The API lives at http://localhost:8000 in dev and behind an ALB in prod.
  // NEXT_PUBLIC_API_URL is set at build/runtime; falls back to localhost:8000.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_API_KEY: process.env.NEXT_PUBLIC_API_KEY || "changeme-local-dev",
  },
  // Required for Docker multi-stage build
  output: "standalone",
};

module.exports = nextConfig;
