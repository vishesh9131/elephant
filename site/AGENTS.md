# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

The canonical Elephant artwork is `site/public/elephant.png`, supplied as `Group 197.png`. Render its original black engraving without brightness, inversion, grayscale, or contrast filters. On cream surfaces, `mix-blend-mode: multiply` may be used only to merge the artwork's white canvas into the page; do not alter the black ink.

Keep the complete feet visible in the hero crop at desktop and mobile breakpoints; position the square source upward instead of enlarging or clipping its lower edge.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.
