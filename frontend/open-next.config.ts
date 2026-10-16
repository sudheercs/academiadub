import type { OpenNextConfig } from "@opennextjs/cloudflare";

// @opennextjs/cloudflare configuration
// See: https://opennext.js.org/cloudflare
const config: OpenNextConfig = {
  default: {
    override: {
      wrapper: "cloudflare-node",
      converter: "edge",
      proxyExternalRequest: "fetch",
      // Use in-memory caches — swap for KV/D1 bindings when you add ISR
      incrementalCache: "dummy",
      tagCache: "dummy",
      queue: "dummy",
    },
  },

  // Required for node:crypto (used by Next.js internals)
  edgeExternals: ["node:crypto"],

  middleware: {
    external: true,
    override: {
      wrapper: "cloudflare-edge",
      converter: "edge",
      proxyExternalRequest: "fetch",
      incrementalCache: "dummy",
      tagCache: "dummy",
      queue: "dummy",
    },
  },
};

export default config;


