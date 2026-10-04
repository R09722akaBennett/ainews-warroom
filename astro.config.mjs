import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import tailwindcss from "@tailwindcss/vite";
import pagefind from "astro-pagefind";

export default defineConfig({
  site: "https://aiwarroom.bennettlabs.dev",
  // Matches wrangler.jsonc html_handling: drop-trailing-slash, so the sitemap
  // and internal links use the same URLs Cloudflare serves without a redirect.
  trailingSlash: "never",

  // Every page is built in Chinese at "/" and in English at "/en/"; the
  // sitemap lists both with hreflang alternates.
  integrations: [
    sitemap({ i18n: { defaultLocale: "zh", locales: { zh: "zh-Hant-TW", en: "en" } } }),
    pagefind(),
  ],

  vite: {
    plugins: [tailwindcss()],
  },

  markdown: {
    shikiConfig: {
      theme: "css-variables",
    },
  },
});
