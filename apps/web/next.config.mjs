/** @type {import('next').NextConfig} */
const apiBase = process.env.API_INTERNAL_URL || "http://localhost:8000";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    // Proxy API calls so the browser shares cookies with /api/* on the same origin.
    return [{ source: "/api/:path*", destination: `${apiBase}/api/:path*` }];
  },
};

export default nextConfig;
