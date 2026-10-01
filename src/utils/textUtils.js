const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/**
 * Convert inline markdown (bold, italics, code, links) to HTML for set:html.
 *
 * The input is HTML-escaped first, so raw tags in it render as text, and a
 * link whose URL is not http(s) or relative keeps only its text. Null or
 * undefined input returns an empty string.
 * @param {string | null | undefined} text The input markdown string.
 * @returns {string} The converted HTML string.
 */
export function markdownToHtml(text) {
  if (!text) return '';

  let html = String(text).replace(/[&<>"']/g, (c) => ESCAPES[c]);

  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/`(.*?)`/g, '<code>$1</code>');
  html = html.replace(/\[(.*?)\]\((.*?)\)/g, (_m, label, url) =>
    /^(?:https?:\/\/|\/|#)/i.test(url) ? `<a href="${url}">${label}</a>` : label
  );

  return html;
}
