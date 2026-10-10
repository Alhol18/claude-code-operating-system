#!/usr/bin/env python3
"""Ukrainian text readability: Hemingway app replacement for Cyrillic.

Problem solved: Sabri Suby advises writing copy, running through hemingwayapp.com,
and cleaning everything flagged red and yellow (source: copywriting criteria,
video 'The 4 Stages to $100k/day', 05:37). Hemingway counts English: its formulas
are tuned to English syllables. On Ukrainian text it stays silent.

Here is the same logic, calculated for Cyrillic: sentence length, syllables per word,
passive voice, adverbs. Numbers instead of impressions.

IMPORTANT on accuracy: Flesch coefficients adapted by Oborneva for Russian and
transferred to Ukrainian approximately. Use RELATIVELY: compare drafts to each
other and clean the hardest sentences, not chase absolute target like 'fifth grade'.

Usage:
    python3 tools/readability_ua.py draft.txt
    pbpaste | python3 tools/readability_ua.py            # from stdin
    python3 tools/readability_ua.py draft.txt --worst 10 # more hard sentences
    python3 tools/readability_ua.py --headline "text"    # check 45-char gate
    python3 tools/readability_ua.py a.txt b.txt          # compare drafts
"""

import argparse
import re
import sys
from pathlib import Path

# Ukrainian vowels (Cyrillic)
VOWELS = set("аеєиіїоуюяАЕЄИІЇОУЮЯ")

# Headline gate: 45 characters
HEADLINE_LIMIT = 45

# Lead text above 'more' button in Meta feed: 11-14 words
LEADIN_WORDS = (11, 14)

# Sentence split on period/exclamation/question or newlines
SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n+")
# Words: Cyrillic or Latin letters, apostrophes, hyphens
WORD_RE = re.compile(r"[А-Яа-яЄЇІЇієїґҐA-Za-z’’\-]+")

# Filler adverbs and literary suffixes. Heuristic, not morphological.
# Ukrainian filler adverbs and adverb-forming suffixes
ADVERB_SUFFIXES = ("ично", "ічно", "ально", "ливо", "ково", "ідно", "ерно", "овно")
ADVERB_FILLER = {
    "дуже", "досить", "доволі", "надзвичайно", "неймовірно", "абсолютно",
    "повністю", "цілком", "справді", "дійсно", "фактично", "практично",
    "власне", "просто", "буквально", "реально", "максимально", "значно",
}

# Passive voice: impersonal forms ending in -ено/-ано/-ято/-уто/-то and reflexives -ся/-сь.
# Narrowed to verb endings only to avoid catching adverbs (надзвичайно, спокійно, точно)
# which also end in -но. Ukrainian passive patterns.
PASSIVE_NOTO = re.compile(r"\w{3,}(ено|ано|яно|ято|уто|нуто)$")
PASSIVE_SJA = re.compile(r"\w{4,}(ся|сь)$")


def syllables(word: str) -> int:
    """Syllable in Ukrainian = vowel. Exact count, unlike English."""
    return sum(1 for ch in word if ch in VOWELS)


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


def words_of(text: str) -> list[str]:
    return WORD_RE.findall(text)


def flesch(asl: float, asw: float) -> float:
    """Flesch Reading Ease, Oborneva coefficients for Cyrillic. Higher = easier."""
    return 206.835 - 1.3 * asl - 60.1 * asw


def grade(asl: float, asw: float) -> float:
    """Reading grade, Oborneva coefficients. Target per Sabri: 5 or below."""
    return 0.5 * asl + 8.4 * asw - 15.59


def band(g: float) -> str:
    """Hemingway bands: red = very hard, yellow = hard."""
    if g >= 14:
        return "red"
    if g >= 10:
        return "yellow"
    return "ok"


def analyze_sentence(sent: str) -> dict:
    ws = words_of(sent)
    if not ws:
        return {}
    syl = sum(syllables(w) for w in ws)
    asl = len(ws)
    asw = syl / len(ws)
    g = grade(asl, asw)
    lower = [w.lower() for w in ws]
    advs = [
        w for w in lower
        if w in ADVERB_FILLER or (len(w) > 5 and w.endswith(ADVERB_SUFFIXES))
    ]
    adv_set = set(advs)
    passives = [
        w for w in lower
        if w not in adv_set and (PASSIVE_NOTO.match(w) or PASSIVE_SJA.match(w))
    ]
    longs = [w for w in ws if syllables(w) >= 4]
    return {
        "text": sent,
        "words": len(ws),
        "syllables": syl,
        "asw": asw,
        "grade": g,
        "band": band(g),
        "adverbs": advs,
        "passives": passives,
        "long_words": longs,
    }


def analyze(text: str) -> dict:
    sents = [analyze_sentence(s) for s in split_sentences(text)]
    sents = [s for s in sents if s]
    if not sents:
        return {}
    total_w = sum(s["words"] for s in sents)
    total_s = sum(s["syllables"] for s in sents)
    asl = total_w / len(sents)
    asw = total_s / total_w
    return {
        "sentences": sents,
        "n_sent": len(sents),
        "n_words": total_w,
        "asl": asl,
        "asw": asw,
        "flesch": flesch(asl, asw),
        "grade": grade(asl, asw),
        "n_red": sum(1 for s in sents if s["band"] == "red"),
        "n_yellow": sum(1 for s in sents if s["band"] == "yellow"),
        "adverbs": [a for s in sents for a in s["adverbs"]],
        "passives": [p for s in sents for p in s["passives"]],
        "long_words": [w for s in sents for w in s["long_words"]],
    }


MARK = {"red": "!!", "yellow": " !", "ok": "  "}


def report(name: str, r: dict, worst: int) -> None:
    if not r:
        print(f"{name}: empty")
        return
    print(f"\n=== {name} ===")
    print(f"  sentences {r['n_sent']}, words {r['n_words']}")
    print(f"  words per sentence    {r['asl']:6.1f}")
    print(f"  syllables per word    {r['asw']:6.2f}")
    print(f"  Flesch                {r['flesch']:6.1f}   (higher = easier; 60+ good)")
    print(f"  reading grade         {r['grade']:6.1f}   (target: <= 5)")
    red, yellow = r["n_red"], r["n_yellow"]
    pct = (red + yellow) / r["n_sent"] * 100
    print(f"  hard sentences        {red} red, {yellow} yellow  ({pct:.0f}%)")
    if r["adverbs"]:
        print(f"  adverbs ({len(r['adverbs'])}): {', '.join(sorted(set(r['adverbs'])))}")
    if r["passives"]:
        print(f"  passive and reflexive ({len(r['passives'])}): {', '.join(sorted(set(r['passives'])))}")
    if r["long_words"]:
        uniq = sorted(set(r["long_words"]), key=lambda w: -syllables(w))[:8]
        print(f"  long words (4+ syllables): {', '.join(uniq)}")

    flagged = [s for s in r["sentences"] if s["band"] != "ok"]
    flagged.sort(key=lambda s: -s["grade"])
    if flagged:
        print(f"\n  Hardest sentences (clean from top):")
        for s in flagged[:worst]:
            t = s["text"] if len(s["text"]) <= 110 else s["text"][:107] + "..."
            print(f"   {MARK[s['band']]} [grade {s['grade']:4.1f} · {s['words']} words] {t}")
    else:
        print("\n  No hard sentences.")


def check_headline(text: str) -> None:
    n = len(text)
    ok = "OK" if n <= HEADLINE_LIMIT else "TOO LONG"
    print(f"headline: {n} chars of {HEADLINE_LIMIT}: {ok}")
    if n > HEADLINE_LIMIT:
        print(f"  remove {n - HEADLINE_LIMIT} characters")
    w = len(words_of(text))
    lo, hi = LEADIN_WORDS
    if lo <= w <= hi:
        print(f"  {w} words: fits and works as 'more' button teaser ({lo}-{hi})")
    r = analyze(text)
    if r:
        print(f"  reading grade {r['grade']:.1f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*", help="files; reads stdin if none given")
    ap.add_argument("--worst", type=int, default=5, help="how many hard sentences to show")
    ap.add_argument("--headline", help="check headline against 45-char gate")
    args = ap.parse_args()

    if args.headline:
        check_headline(args.headline)
        return

    if args.files:
        for f in args.files:
            p = Path(f)
            if not p.exists():
                print(f"no file: {f}", file=sys.stderr)
                continue
            report(p.name, analyze(p.read_text(encoding="utf-8")), args.worst)
    else:
        data = sys.stdin.read()
        if not data.strip():
            ap.error("empty input")
        report("stdin", analyze(data), args.worst)


if __name__ == "__main__":
    main()
