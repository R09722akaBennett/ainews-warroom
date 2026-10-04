/**
 * UI copy in both languages.
 *
 * Each page area keeps its strings in ./ui/<area>.ts as { zh: {...}, en: {...} }
 * with the same keys; this file merges them. The Chinese object is the type,
 * so a key missing from English fails `astro check`.
 */
import { common } from "./ui/common";

const zh = { ...common.zh };
const en: typeof zh = { ...common.en };

export type UI = typeof zh;
export const ui = { zh, en } as const;
