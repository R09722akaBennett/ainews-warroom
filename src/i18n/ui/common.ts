export const common = {
  zh: {
    siteDescription: "每日 AI 快報、前沿實驗室動態與產業趨勢",
    nav: {
      sources: "Sources", reports: "Reports", insights: "Insights", reading: "Reading", podcasts: "Podcasts",
      leaderboard: "Leaderboard", trending: "Trending", labs: "Labs", analytics: "Analytics", archive: "Archive", about: "About",
    },
    header: { search: "搜尋", theme: "切換深淺色", menu: "開關選單", switchLang: "English", switchLangTitle: "Read in English" },
    search: { label: "搜尋", hint: "按 Esc 或點擊外側即可關閉。", copyCode: "複製程式碼" },
    pagination: { label: "分頁", prev: "上一頁", next: "下一頁", status: (cur: number, last: number) => `第 ${cur} 頁，共 ${last} 頁`, page: (n: number) => `第 ${n} 頁` },
    backToTop: "回到頂端",
    notTranslated: "這篇還沒有中文版，以下是原文。",
    notFound: { title: "找不到頁面", description: "這個網址沒有對應的頁面", heading: "找不到這個頁面", body: "網址可能打錯了，或頁面已經移到別的地方。", home: "回到首頁", reports: "每日快報" },
  },
  en: {
    siteDescription: "Daily AI digest, frontier-lab tracker and industry trends",
    nav: {
      sources: "Sources", reports: "Reports", insights: "Insights", reading: "Reading", podcasts: "Podcasts",
      leaderboard: "Leaderboard", trending: "Trending", labs: "Labs", analytics: "Analytics", archive: "Archive", about: "About",
    },
    header: { search: "Search", theme: "Toggle theme", menu: "Toggle menu", switchLang: "中文", switchLangTitle: "切換到中文" },
    search: { label: "Search", hint: "Press Esc or click outside to close.", copyCode: "Copy code" },
    pagination: { label: "Pagination", prev: "Previous", next: "Next", status: (cur: number, last: number) => `Page ${cur} of ${last}`, page: (n: number) => `Page ${n}` },
    backToTop: "Back to top",
    notTranslated: "This entry has no English version yet; the original follows.",
    notFound: { title: "Page not found", description: "No page lives at this address", heading: "This page does not exist", body: "The address may be mistyped, or the page has moved.", home: "Back to home", reports: "Daily digest" },
  },
};
