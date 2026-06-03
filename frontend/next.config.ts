import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Turbopack (default in Next.js 16) needs system TLS certs to fetch
    // Google Fonts at build time. Without this flag the font download fails
    // in environments where Node's bundled certs don't cover the CDN.
    turbopackUseSystemTlsCerts: true,
  },
};

export default nextConfig;
