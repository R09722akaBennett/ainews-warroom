import podcastsData from "../../data/podcasts.json";
import type { EpisodeSummary } from "@lib/podcasts";

export const PER_PAGE = 20;
export const episodes = ((podcastsData as unknown as { episodes: EpisodeSummary[] }).episodes || [])
  .slice()
  .sort((a, b) => b.date.localeCompare(a.date));
