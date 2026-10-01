import readingData from "../../data/reading.json";

export type Item = { id: string; source: string; title: string; url: string | null; date: string; summary: string; summarised: boolean; headings: string[]; sections?: { title: string }[] };
const data = readingData as { sources: { key: string; name: string; cadence: string }[]; items: Item[] };

export const PER_PAGE = 20;
export const items = data.items;
export const sources = data.sources.filter((s) => items.some((i) => i.source === s.key));
export const nameOf = new Map(data.sources.map((s) => [s.key, s.name]));

// Source keys look like "gmail:daily_dose_of_ds"; the URL keeps only the
// readable tail.
export const sourceSlug = (key: string) => key.split(":").pop()!.replace(/_/g, "-");
export const sourceHref = (key: string) => `/reading/source/${sourceSlug(key)}`;
export const itemsOf = (key: string) => items.filter((i) => i.source === key);
