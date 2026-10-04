import type { PaginateFunction } from "astro";

export type PageSlice<T> = {
  data: T[];
  start: number;
  end: number;
  total: number;
  currentPage: number;
  lastPage: number;
};

/**
 * Build the link for page `n` of a list rooted at `base`.
 *
 * Page 1 is the base path itself so the nav links keep working; later pages
 * live at `<base>/page/<n>`. Links never end with a slash because the
 * Workers asset handler redirects those.
 */
export function pageHref(base: string, n: number): string {
  return n <= 1 ? base : `${base}/page/${n}`;
}

/** Slice page 1 the same way `paginate()` does, for the base route. */
export function firstPage<T>(items: T[], size: number): PageSlice<T> {
  const end = Math.min(size, items.length);
  return { data: items.slice(0, end), start: 0, end: end - 1, total: items.length, currentPage: 1, lastPage: Math.max(1, Math.ceil(items.length / size)) };
}

/**
 * Return the static paths for pages 2..N of `items`.
 *
 * The `page/[page].astro` routes include the page number in every path, so
 * `paginate()` also emits `/page/1`; that duplicate of the base route is
 * dropped here.
 */
export function laterPages<T>(paginate: PaginateFunction, items: T[], size: number, params: Record<string, string> = {}, props: Record<string, unknown> = {}) {
  return paginate(items, { pageSize: size, params, props }).filter((p) => p.props.page.currentPage > 1);
}
