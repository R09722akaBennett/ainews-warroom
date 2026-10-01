import { Marked, type Tokens } from "marked";

const ESCAPES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

// Relative, fragment, http(s) and mailto links only; a javascript: or data:
// href from model output would otherwise survive escaping.
const SAFE_HREF = /^(?:https?:|mailto:|#|\/|\.\.?\/)/i;

// A private instance, so these overrides never leak into other callers of the
// shared `marked` singleton.
const parser = new Marked({
  renderer: {
    html({ text }: Tokens.HTML | Tokens.Tag) {
      return escapeHtml(text);
    },
    link(token: Tokens.Link) {
      if (SAFE_HREF.test(token.href.trim())) return false;
      return this.parser.parseInline(token.tokens);
    },
  },
});

/**
 * Render markdown from generated content into HTML that is safe for set:html.
 *
 * Markdown formatting is kept, but raw HTML in the source is escaped and shows
 * up as literal text, and links with any scheme other than http(s) or mailto
 * are reduced to their text. An empty or missing input returns an empty
 * string.
 */
export function renderMarkdown(md: string): string {
  return parser.parse(md || "", { async: false }) as string;
}
