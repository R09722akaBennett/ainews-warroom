import leaderboard from "@data/leaderboard.json";

export const ROWS_PER_PAGE = 100;
export const categories = (leaderboard as any).categories as Record<string, any[]>;
/** Table rows of a category; the top three sit in the podium instead. */
export const tableRows = (key: string) => categories[key].slice(3);
