import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

// Produces a single self-contained dist/index.html with all JS, CSS, and the
// inlined data.json — no backend, no external requests. Ideal as a citable,
// offline, archival artifact (e.g. a Zenodo upload).
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: {
    target: "es2020",
    assetsInlineLimit: 100_000_000,
    chunkSizeWarningLimit: 100_000,
    cssCodeSplit: false,
  },
});
