export type Guest = { name: string; role?: string; links?: Record<string, string> };

export type EpisodeSummary = {
  slug: string;
  show: string;
  title: string;
  subtitle: string;
  date: string;
  url: string;
  youtube: string | null;
  duration: number;
  image: string | null;
  guests: Guest[];
  one_liner: string;
  topics: string[];
  words: number;
  tokenUsage: { input: number; output: number; total: number } | null;
};

export type Turn = { speaker: string; t: string; seconds: number; text: string };

export type Episode = Omit<EpisodeSummary, "one_liner" | "topics" | "words"> & {
  intro: string[] | null;
  we_discuss: string[] | null;
  chapters: { t: string; seconds: number; title: string }[] | null;
  transcript: { title: string; turns: Turn[] }[] | null;
  summary: {
    one_liner?: string;
    topics?: { title: string; body: string }[];
    insights?: { title: string; body: string }[];
    quotes?: { speaker: string; en: string; zh: string }[];
    guests?: { name: string; intro: string }[];
  };
};

const HOSTS = ["swyx", "alessio", "vibhu"];

export function isHost(speaker: string): boolean {
  const s = speaker.trim().toLowerCase();
  return HOSTS.some((h) => s === h || s.startsWith(h + " "));
}

export function minutes(seconds: number): string {
  return `${Math.max(1, Math.round((seconds || 0) / 60))} 分鐘`;
}

// The site rebuilds daily, so "today" is the build date in Taiwan time.
export function buildToday(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Taipei" }).format(new Date());
}

function daysBetween(a: string, b: string): number {
  return Math.round((Date.parse(b + "T00:00:00Z") - Date.parse(a + "T00:00:00Z")) / 86_400_000);
}

export function recencyLabel(date: string, today: string): string | null {
  const d = daysBetween(date, today);
  if (d === 0) return "今天";
  if (d === 1) return "昨天";
  if (d >= 2 && d <= 6) return "本週";
  return null;
}

export function youtubeAt(youtube: string, seconds: number): string {
  return `${youtube}${youtube.includes("?") ? "&" : "?"}t=${seconds}s`;
}
