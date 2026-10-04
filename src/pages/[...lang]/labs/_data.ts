import { renderMarkdown } from "@lib/markdown";
import { SITE_SINCE } from "@consts";
import { href, type Lang } from "@i18n";
import { labsUI } from "@i18n/ui/labs";
import labsData from "../../../data/labs.json";
import summariesData from "../../../data/summaries.json";

export type Lab = { key: string; name: string; tier: number; region: string; openness: string };
type RawItem = { date: string; lab: string; title: string; url: string; source: string; publishedAt: string; category: string; summary: string; content: string; aliases?: string[]; en?: { summary?: string } };
export type Post = RawItem & { day: string; time: string; id: string };
export type Summary = { period: string; startDate: string; endDate: string; title: string; content: string; tags?: any; tokenUsage?: { input?: number; output?: number }; en?: { title?: string; content?: string } };

export const labsMeta = (labsData as any).labs as Lab[];
export const updatedAt = (labsData as any).updatedAt as string | undefined;
export const labByKey = new Map(labsMeta.map((l) => [l.key, l]));
export const labName = (key: string) => labByKey.get(key)?.name || key;

// Taiwan has no DST, so a fixed +8h offset is exact and avoids depending on the
// build machine's ICU data.
export function taipei(iso: string): Date {
  return new Date(new Date(iso).getTime() + 8 * 3600 * 1000);
}
export const pad = (n: number) => String(n).padStart(2, "0");
export function dayLabel(lang: Lang, ymd: string): string {
  const ui = labsUI[lang];
  const d = new Date(`${ymd}T00:00:00Z`);
  return ui.dayLabel(`${pad(d.getUTCMonth() + 1)}/${pad(d.getUTCDate())}`, ui.weekdays[d.getUTCDay()]);
}
export const shortDate = (ymd: string) => ymd.slice(5).replace("-", "/");
export const tokens = (lang: Lang, u?: { input?: number; output?: number }) =>
  u ? labsUI[lang].tokens(u.input?.toLocaleString() ?? "–", u.output?.toLocaleString() ?? "–") : "";
export const updatedLabel = updatedAt
  ? (() => {
      const t = taipei(updatedAt);
      return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())} ${pad(t.getUTCHours())}:${pad(t.getUTCMinutes())}`;
    })()
  : "";

// The exported `date` is the run date, which can be a day after the Taipei
// publish date for evening posts, so the day and the time label both come
// from publishedAt.
export const posts: Post[] = (((labsData as any).items || []) as RawItem[])
  .map((item) => {
    const t = item.publishedAt ? taipei(item.publishedAt) : null;
    const day = t ? `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())}` : item.date;
    const time = t ? `${pad(t.getUTCHours())}:${pad(t.getUTCMinutes())}` : "";
    return { ...item, day, time, id: `post-${item.url.split("/").pop()}` };
  })
  .filter((p) => p.day >= SITE_SINCE)
  .sort((a, b) => (b.publishedAt || b.date).localeCompare(a.publishedAt || a.date));

const summaries = summariesData as unknown as Summary[];
export const briefByDay = new Map(
  summaries.filter((s) => s.period === "labs_daily" && s.startDate >= SITE_SINCE).map((s) => [s.startDate, s] as [string, Summary]),
);
export const weeklyReports = summaries
  .filter((s) => s.period === "labs_weekly")
  .sort((a, b) => b.endDate.localeCompare(a.endDate));

export const postsByDay = new Map<string, Post[]>();
for (const p of posts) {
  if (!postsByDay.has(p.day)) postsByDay.set(p.day, []);
  postsByDay.get(p.day)!.push(p);
}
/** Every day with posts or a brief, newest first. */
export const days = [...new Set([...postsByDay.keys(), ...briefByDay.keys()])].sort().reverse();

// Slugs in display order; the labels live in the dictionary.
const categoryLabels = labsUI.zh.categories;
// The tag prints its label in this color, so these are the text-safe tokens.
const categoryColors: Record<string, string> = {
  model_release: "var(--color-quarterly-text)",
  product: "var(--color-monthly-text)",
  research: "var(--color-accent-cool-text)",
  open_source: "var(--color-accent-purple-text)",
  infra: "var(--color-accent-warm-text)",
  partnership: "var(--color-accent-orange-text)",
  funding: "var(--color-accent-orange-text)",
  talent: "var(--color-accent-purple-text)",
  policy: "var(--color-danger-text)",
  event: "var(--color-monthly-text)",
  other: "var(--color-text-muted-on-muted)",
};
export const catLabel = (lang: Lang, c: string) => labsUI[lang].categories[c] || c.replace(/_/g, " ");
export const catColor = (c: string) => categoryColors[c] || "var(--color-text-muted-on-muted)";

export function countBy<T>(list: T[], key: (i: T) => string | undefined): Map<string, number> {
  const m = new Map<string, number>();
  for (const i of list) {
    const k = key(i);
    if (k) m.set(k, (m.get(k) || 0) + 1);
  }
  return m;
}
export function sortLabs(keys: string[], counts: Map<string, number>): string[] {
  return keys.sort(
    (a, b) => (labByKey.get(a)?.tier ?? 9) - (labByKey.get(b)?.tier ?? 9) || (counts.get(b) || 0) - (counts.get(a) || 0) || labName(a).localeCompare(labName(b)),
  );
}
export function sortCats(counts: Map<string, number>): string[] {
  return [...Object.keys(categoryLabels).filter((c) => counts.has(c)), ...[...counts.keys()].filter((c) => !(c in categoryLabels)).sort()];
}

export const labCounts = countBy(posts, (p) => p.lab);
/** Labs with at least one post, which are the ones that get a page. */
export const activeLabs = sortLabs([...labCounts.keys()], labCounts);
export const labHref = (lang: Lang, key: string) => href(lang, `/labs/lab/${encodeURIComponent(key)}`);
export const dayHref = (lang: Lang, day: string) => href(lang, `/labs/${day}`);

/** Swap point for the shared markdown renderer. */
export function render(md: string): string {
  return renderMarkdown(md || "");
}

const postByUrl = new Map<string, Post>(posts.flatMap((p) => [p.url, ...(p.aliases || [])].map((u) => [u, p] as [string, Post])));

/**
 * Render a brief and point its post citations at the post cards.
 *
 * A post on `currentDay` becomes an in-page anchor that the page script
 * highlights; a post on another day links to that day's page; anything else
 * stays an external link in a new tab. Pass no day for pages without cards.
 * Links keep the language of the page they are rendered on.
 */
export function renderBrief(lang: Lang, md: string, currentDay?: string): string {
  return render(md).replace(/<a href="([^"]+)"([^>]*)>([\s\S]*?)<\/a>/g, (whole, url: string, _rest: string, text: string) => {
    const post = postByUrl.get(url.replace(/&amp;/g, "&"));
    if (post && post.day === currentDay) {
      return `<a href="#${post.id}" class="lab-ref" data-target="${post.id}">${text}</a>`;
    }
    if (post) {
      return `<a href="${dayHref(lang, post.day)}#${post.id}" class="lab-ref">${text}</a>`;
    }
    return whole.replace("<a ", '<a target="_blank" rel="noopener" ');
  });
}

// The first markdown block (usually the 本週重點 list) is the teaser; the rest
// opens on demand so the latest report stays short on a phone.
export function splitWeekly(md: string): { lead: string; rest: string } {
  const blocks = (md || "").trim().split(/\n\s*\n/);
  let i = 0;
  const lead: string[] = [];
  while (i < blocks.length && /^#{1,6}\s/.test(blocks[i].trim()) && !blocks[i].trim().includes("\n")) lead.push(blocks[i++]);
  if (i < blocks.length) lead.push(blocks[i++]);
  return { lead: lead.join("\n\n"), rest: blocks.slice(i).join("\n\n") };
}
