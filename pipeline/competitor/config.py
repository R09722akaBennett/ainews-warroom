"""Competitor definitions — companies, queries, and RSS feeds."""

COMPETITORS = {
    # === Tier 1: PDF & eSign (direct competitors) ===
    "adobe": {
        "name": "Adobe",
        "tier": 1,
        "domain": "PDF / eSign / Creative",
        "google_queries": [
            '"Adobe" (AI OR "Acrobat AI" OR Firefly OR "Adobe Sign") when:3d',
        ],
        "rss_feeds": {
            "Adobe Blog": "https://blog.adobe.com/feed",
        },
    },
    "docusign": {
        "name": "DocuSign",
        "tier": 1,
        "domain": "eSign",
        "google_queries": [
            '"DocuSign" (AI OR IAM OR "intelligent agreement") when:3d',
        ],
        "rss_feeds": {},
    },
    "foxit": {
        "name": "Foxit",
        "tier": 1,
        "domain": "PDF",
        "google_queries": [
            '"Foxit" (AI OR PDF) when:3d',
        ],
        "rss_feeds": {},
    },
    "smallpdf": {
        "name": "Smallpdf",
        "tier": 1,
        "domain": "PDF",
        "google_queries": [
            '"Smallpdf" when:3d',
        ],
        "rss_feeds": {},
    },
    "pandadoc": {
        "name": "PandaDoc",
        "tier": 1,
        "domain": "eSign",
        "google_queries": [
            '"PandaDoc" (AI OR eSign OR document) when:3d',
        ],
        "rss_feeds": {
            "PandaDoc Blog": "https://www.pandadoc.com/blog/feed/",
        },
    },
    # === Tier 1: Creative & Productivity ===
    "canva": {
        "name": "Canva",
        "tier": 1,
        "domain": "Creative",
        "google_queries": [
            '"Canva" (AI OR "Magic Studio" OR "Magic Design") when:3d',
        ],
        "rss_feeds": {},
    },
    "notion": {
        "name": "Notion",
        "tier": 1,
        "domain": "Productivity",
        "google_queries": [
            '"Notion" AI when:3d',
        ],
        "rss_feeds": {},
    },
    # === Tier 1: Marketing & Ads (ADNEX competitors) ===
    "hubspot": {
        "name": "HubSpot",
        "tier": 1,
        "domain": "Marketing Automation",
        "google_queries": [
            '"HubSpot" AI when:3d',
        ],
        "rss_feeds": {
            "HubSpot Marketing Blog": "https://blog.hubspot.com/marketing/rss.xml",
        },
    },
    "mailchimp": {
        "name": "Mailchimp",
        "tier": 1,
        "domain": "Email / Ads",
        "google_queries": [
            '"Mailchimp" AI when:3d',
        ],
        "rss_feeds": {},
    },
    "jasper": {
        "name": "Jasper",
        "tier": 1,
        "domain": "AI Content",
        "google_queries": [
            '"Jasper AI" when:3d',
        ],
        "rss_feeds": {},
    },
    "copyai": {
        "name": "Copy.ai",
        "tier": 1,
        "domain": "AI Content",
        "google_queries": [
            '"Copy.ai" when:3d',
        ],
        "rss_feeds": {},
    },
    "hootsuite": {
        "name": "Hootsuite",
        "tier": 1,
        "domain": "Social Marketing",
        "google_queries": [
            '"Hootsuite" AI when:3d',
        ],
        "rss_feeds": {
            "Hootsuite Blog": "https://blog.hootsuite.com/feed",
        },
    },
    "buffer": {
        "name": "Buffer",
        "tier": 1,
        "domain": "Social Marketing",
        "google_queries": [
            '"Buffer" AI when:3d',
        ],
        "rss_feeds": {
            "Buffer Blog": "https://buffer.com/resources/feed",
        },
    },
    "semrush": {
        "name": "SEMrush",
        "tier": 1,
        "domain": "SEO / Marketing",
        "google_queries": [
            '"SEMrush" AI when:3d',
        ],
        "rss_feeds": {
            "SEMrush Blog": "https://www.semrush.com/blog/feed",
        },
    },
}
