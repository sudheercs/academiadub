/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: false,
  },
  async headers() {
    return [
      {
        source: "/workers/codelab.worker.js",
        headers: [
          {
            key: "Content-Security-Policy",
            value: "default-src 'none'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-eval' 'wasm-unsafe-eval'; connect-src https://cdn.jsdelivr.net;",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
