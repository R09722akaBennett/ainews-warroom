/**
 * Bilingual routing and data helpers.
 *
 * Every page lives under src/pages/[...lang]/ and is built twice: with the
 * rest param undefined for Traditional Chinese at "/" and with "en" for
 * English at "/en/". Data files carry the native language in their usual
 * fields and the other language under "en" or "zh"; pick() merges the one
 * the page needs. UI copy comes from the dictionaries in ./ui.
 */
import { ui, type UI } from "./ui";

export type Lang = "zh" | "en";
export const LANGS: Lang[] = ["zh", "en"];
export const DEFAULT_LANG: Lang = "zh";

/** The lang param values getStaticPaths must emit: undefined (Chinese at "/") and "en". */
export const LANG_PARAMS: { lang: string | undefined }[] = [{ lang: undefined }, { lang: "en" }];

/** Cross a route's own static paths with both languages. */
export function withLangs<P extends { params: Record<string, string | number | undefined>; props?: Record<string, unknown> }>(paths: P[]): P[] {
  return LANG_PARAMS.flatMap(({ lang }) => paths.map((p) => ({ ...p, params: { ...p.params, lang } })));
}

export function langOf(params: Record<string, string | undefined>): Lang {
  return params.lang === "en" ? "en" : "zh";
}

export function htmlLang(lang: Lang): string {
  return lang === "en" ? "en" : "zh-Hant-TW";
}

/** Prefix an internal path for the language; "/" in English is "/en". */
export function href(lang: Lang, path: string): string {
  if (lang !== "en") return path;
  if (path === "/" || path === "") return "/en";
  return path.startsWith("/") ? `/en${path}` : path;
}

/** Strip the "/en" prefix so the same page can be addressed in either language. */
export function stripLang(pathname: string): string {
  const p = pathname.replace(/\/+$/, "") || "/";
  if (p === "/en") return "/";
  return p.startsWith("/en/") ? p.slice(3) : p;
}

export function langOfPath(pathname: string): Lang {
  const p = pathname.replace(/\/+$/, "") || "/";
  return p === "/en" || p.startsWith("/en/") ? "en" : "zh";
}

/** The dictionary for the language, typed by the Chinese one so both must carry every key. */
export function t(lang: Lang): UI {
  return ui[lang];
}

/**
 * Return the item with the language's fields merged in.
 *
 * Chinese-native data (reports, briefs, podcast summaries) carries "en";
 * English-native data (reading) carries "zh". When the page's language is
 * the native one, or the translation is missing, the item comes back as it
 * is; `translated` says whether the text shown is in the page's language.
 */
export function pick<T extends object>(item: T, lang: Lang, native: Lang): { data: T; translated: boolean } {
  if (lang === native) return { data: item, translated: true };
  const extra = (item as Record<string, unknown>)[lang];
  if (!extra || typeof extra !== "object") return { data: item, translated: false };
  return { data: { ...item, ...(extra as Partial<T>) }, translated: true };
}

/** A date for display: "2026-10-03" in Chinese pages, "Oct 3, 2026" in English. */
export function fmtDate(lang: Lang, iso: string): string {
  if (lang !== "en" || !/^\d{4}-\d{2}-\d{2}/.test(iso)) return iso;
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
}
