"""Parse a Latent Space podcast post (Substack body_html) into an episode dict.

Latent Space posts carry, as <h2> sections in this order: an editor's intro,
"We discuss:" (a bullet list), one section per guest (role line plus X /
LinkedIn links), "Timestamps" (bold hh:mm:ss lines) and, under an <h1>
"Transcript", one <h2> per chapter with paragraphs that open with a bold
"Speaker [hh:mm:ss]:". Sections that do not fit these shapes stay in the
intro, so a post that drops one of them still parses.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

TIME = re.compile(r"^\s*(\d{1,2}):(\d{2}):(\d{2})\s*$")
TURN = re.compile(r"^\s*(.{1,60}?)\s*\[(\d{1,2}:\d{2}:\d{2})\]\s*:?\s*$")
LINK_LABEL = re.compile(r"^\s*([^:]{1,40}):\s*$")


def _seconds(t: str) -> int:
    h, m, s = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s


def _text(el: Tag) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def _guests(name: str, ul: Tag) -> list[dict]:
    """Return the guest cards in one guest section's list.

    Each "<strong>Label:</strong> <a>" item is a link (X, LinkedIn, a company
    site); the first item without one is the role. The OpenRouter
    episode post nests the next guest's <h2> inside the first guest's list,
    so a heading inside the list starts a new card.
    """
    cards, cur = [], {"name": name, "role": "", "links": {}}
    for el in ul.find_all(["li", "h2", "h3"]):
        if el.name in ("h2", "h3"):
            cards.append(cur)
            cur = {"name": _text(el), "role": "", "links": {}}
            continue
        if el.find(["h2", "h3"]):
            el = BeautifulSoup(str(el), "html.parser")
            for h in el.find_all(["h2", "h3"]):
                h.decompose()
        strong, a = el.find("strong"), el.find("a", href=True)
        label = LINK_LABEL.match(strong.get_text()) if strong else None
        if label and a:
            cur["links"][label.group(1).strip()] = a["href"].split("?")[0]
        elif not cur["role"] and _text(el):
            cur["role"] = _text(el)
    cards.append(cur)
    return [c for c in cards if c["links"]]


def parse_episode(body_html: str) -> dict:
    """Return {"intro", "we_discuss", "guests", "chapters", "transcript", "youtube"}.

    transcript is [{"title", "turns": [{"speaker", "t", "seconds", "text"}]}];
    turns without a speaker label continue the previous turn.
    """
    soup = BeautifulSoup(body_html, "html.parser")
    yt = re.search(r"youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=)([\w-]{11})", body_html)
    out = {"intro": [], "we_discuss": [], "guests": [], "chapters": [], "transcript": [],
           "youtube": f"https://www.youtube.com/watch?v={yt.group(1)}" if yt else None}
    section, in_transcript, chapter = "intro", False, None
    for el in soup.find_all(["h1", "h2", "h3", "p", "ul", "ol"], recursive=True):
        if el.find_parent(["ul", "ol"]):
            continue  # list content, including a heading nested in a list, is read with its list
        if el.name in ("h1", "h2", "h3"):
            title = _text(el)
            low = title.lower().rstrip(":")
            if low == "transcript":
                in_transcript, section = True, "transcript"
            elif in_transcript:
                chapter = {"title": title, "turns": []}
                out["transcript"].append(chapter)
            elif low.startswith("we discuss") or low in ("in this episode", "topics"):
                section = "we_discuss"
            elif low in ("timestamps", "chapters", "show notes timestamps"):
                section = "chapters"
            else:
                section = ("guest", title)
            continue
        if in_transcript:
            if el.name != "p":
                continue
            strong = el.find("strong")
            label = TURN.match(strong.get_text()) if strong else None
            if chapter is None:
                chapter = {"title": "", "turns": []}
                out["transcript"].append(chapter)
            if label:
                strong.extract()
                chapter["turns"].append({"speaker": label.group(1).strip(), "t": label.group(2),
                                         "seconds": _seconds(label.group(2)), "text": _text(el)})
            elif chapter["turns"] and _text(el):
                chapter["turns"][-1]["text"] += "\n\n" + _text(el)
            continue
        if section == "we_discuss" and el.name in ("ul", "ol"):
            out["we_discuss"] += [_text(li) for li in el.find_all("li") if _text(li)]
        elif section == "chapters" and el.name == "p":
            strong = el.find("strong")
            if strong and TIME.match(strong.get_text()):
                t = strong.get_text().strip()
                strong.extract()
                out["chapters"].append({"t": t, "seconds": _seconds(t), "title": _text(el)})
        elif isinstance(section, tuple) and el.name in ("ul", "ol"):
            g = _guests(section[1], el)
            if g:
                out["guests"] += g
            else:
                out["intro"].append(_text(el))
        elif el.name == "p" and _text(el):
            out["intro"].append(_text(el))  # editor's notes, including sections under their own heading
    out["transcript"] = [c for c in out["transcript"] if c["turns"]]
    return out
