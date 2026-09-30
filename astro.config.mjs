import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import tailwindcss from "@tailwindcss/vite";
import vercel from "@astrojs/vercel";
import pagefind from "astro-pagefind";

export default defineConfig({
  site: "https://ainews-warroom.vercel.app",

  integrations: [sitemap(), pagefind()],

  vite: {
    plugins: [tailwindcss()],
  },

  markdown: {
    shikiConfig: {
      theme: "css-variables",
    },
  },

  adapter: vercel(),
});
