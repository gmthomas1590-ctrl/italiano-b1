"""Convert the plain-text daily study email into the app's JSON format.

Usage: python3 tools/parse_email.py YYYY-MM-DD email.txt
Writes days/YYYY-MM-DD.json and rebuilds days/index.json.
"""
import json, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DAYS = ROOT / "days"
DASH = " – "


def parse(text):
    lines = [l.rstrip() for l in text.replace("\r", "").split("\n")]
    head = re.match(r"GIORNO (\d+) DI \d+ – SETTIMANA (\d+): (.+)", lines[0], re.I)
    if not head:
        raise ValueError("Unrecognised header: " + lines[0])
    out = {"day": int(head[1]), "week": int(head[2]), "theme": head[3].strip(),
           "grammar": "", "words": [], "sentences": [], "schema": "", "review": []}
    sec = None
    sent = None
    schema = []
    review_it = []
    for l in lines[1:]:
        s = l.strip()
        up = s.upper()
        if s.lower().startswith("grammar focus:"):
            out["grammar"] = s.split(":", 1)[1].strip(); continue
        if up.startswith("20 PAROLE"): sec = "w"; continue
        if up.startswith("5 FRASI"): sec = "f"; continue
        if up.startswith("SCHEMA DEL GIORNO"): sec = "s"; continue
        if up.startswith("RIPASSO"): sec = "r"; continue
        if s.startswith("-----"): sec = "a"; continue
        if sec == "w":
            m = re.match(r"\d+\.\s+(.*)", s)
            if m:
                parts = m[1].split(DASH)
                it = parts[0].strip()
                ex = parts[-1].strip() if len(parts) >= 3 else ""
                en = DASH.join(parts[1:-1] if len(parts) >= 3 else parts[1:]).strip()
                out["words"].append({"it": it, "en": en, "ex": ex})
        elif sec == "f":
            m = re.match(r"\d+\.\s+(.*)", s)
            if m:
                sent = {"it": m[1], "en": "", "note": ""}
                out["sentences"].append(sent)
            elif s.lower().startswith("nota:") and sent:
                sent["note"] = s.split(":", 1)[1].strip()
            elif s and sent and not sent["en"]:
                sent["en"] = s
        elif sec == "s":
            if l.strip():
                schema.append(l)
        elif sec == "r":
            m = re.match(r"\d+\.\s+(.*)", s)
            if m:
                review_it.append(m[1])
        elif sec == "a" and s.lower().startswith("risposte:"):
            ans = re.split(r"\s*·\s*", s.split(":", 1)[1].strip())
            ans = [re.sub(r"^\d+\.\s*", "", a) for a in ans]
            for i, it in enumerate(review_it):
                out["review"].append({"it": it, "en": ans[i] if i < len(ans) else ""})
    out["schema"] = "\n".join(schema)
    if not out["review"]:
        out["review"] = [{"it": it, "en": ""} for it in review_it]
    return out


def rebuild_index():
    items = []
    for f in sorted(DAYS.glob("2*.json")):
        d = json.loads(f.read_text())
        items.append({"date": d["date"], "day": d["day"], "week": d["week"], "theme": d["theme"]})
    (DAYS / "index.json").write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n")


def save(date, text):
    d = parse(text)
    d["date"] = date
    assert len(d["words"]) >= 10 and d["sentences"], "parse looks incomplete"
    DAYS.mkdir(exist_ok=True)
    (DAYS / f"{date}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    return d


if __name__ == "__main__":
    date, path = sys.argv[1], sys.argv[2]
    d = save(date, pathlib.Path(path).read_text(encoding="utf-8"))
    rebuild_index()
    print(f"Saved {date}: day {d['day']}, {len(d['words'])} words, {len(d['sentences'])} sentences")
