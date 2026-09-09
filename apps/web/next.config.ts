import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      // Evidence PDF uploads are capped at 25 MB by the UI and API.
      bodySizeLimit: "25mb",
    },
  },
};

export default nextConfig;

