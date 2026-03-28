import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "cytoscape-cose-bilkent": "/src/shims/cytoscape-cose-bilkent.js",
      "bin-pack": "/src/shims/bin-pack.js",
      "@neo4j-bloom/dagre": "/src/shims/neo4j-bloom-dagre.js",
      "graphlib": "/src/shims/graphlib.js",
      "cose-base": "/src/shims/cose-base.js",
      "layout-base": "/src/shims/layout-base.js",
      "@segment/analytics-next": "/src/shims/segment-analytics-next.js",
    },
  },
  optimizeDeps: {
    exclude: ["@neo4j-nvl/base", "@neo4j-nvl/layout-workers"],
  },
  server: {
    port: 5173,
  },
});
