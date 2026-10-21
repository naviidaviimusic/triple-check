"""Fact base + numeric claim verification.

A fact is a dict:  {"value": 7, "unit": "years", "lo": 6, "hi": 8,
                    "confidence": "HIGH", "as_of": 2024, "note": "..."}
Numbers in the real world are ranges, so every numeric fact carries lo/hi.
Text facts (no number) are used only to ground the experts' prompts.
"""

import re
from typing import Callable, Optional

# Number + EXPLICIT scale word only. Single-letter scales (m/b) are too
# ambiguous ("8 bottles" → 8 billion) so they are deliberately excluded.
NUM_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(million|billion|thousand)?\b", re.I)
SCALE = {"thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}

# A number followed by one of these is a size or quantity ("750 ml", "5,000 acres"),
# not the per-unit figure an anchor tracks, so it is skipped.
DEFAULT_UNITS_AFTER = r"ml|l\b|litre|liter|kg|gram|oz|acres?|hectares?|tonnes?|tons?"

RATE_AFTER = re.compile(r"\s*(per\b|/)")

STATUSES = ("CONFIRMED", "CLOSE", "DISPUTED", "NO_ANCHOR")


class FactBase:
    def __init__(self, facts: dict, hints: list, units_after: str = DEFAULT_UNITS_AFTER):
        """facts: key -> fact dict.  hints: [(regex, key), ...] — words in text that
        point a nearby number at a fact (e.g. (r"per\\s+acre", "plants_per_acre"))."""
        self.facts = facts
        self.hints = [(re.compile(p), k) for p, k in hints]
        self.unit_after = re.compile(rf"\s*({units_after})")

    # ── verdict for one number ──────────────────────────────────────────────
    def cross_check(self, key: str, claimed, tol: float = 0.30) -> dict:
        """CONFIRMED inside [lo, hi] · CLOSE within tol of the central value ·
        DISPUTED further off · NO_ANCHOR nothing numeric to check against."""
        fact = self.facts.get(key)
        if not fact or not isinstance(fact.get("value"), (int, float)):
            return {"status": "NO_ANCHOR", "key": key, "claimed": claimed, "expected": None}
        expected = float(fact["value"])
        lo, hi = float(fact.get("lo", expected)), float(fact.get("hi", expected))
        try:
            c = float(claimed)
        except (TypeError, ValueError):
            return {"status": "NO_ANCHOR", "key": key, "claimed": claimed, "expected": expected}
        if lo <= c <= hi:
            status = "CONFIRMED"
        elif expected and abs(c - expected) / abs(expected) <= tol:
            status = "CLOSE"
        else:
            status = "DISPUTED"
        return {"status": status, "key": key, "claimed": c, "expected": expected,
                "lo": lo, "hi": hi, "confidence": fact.get("confidence"), "note": fact.get("note", "")}

    # ── find numeric claims in free text ────────────────────────────────────
    def extract_claims(self, text: str, max_dist: int = 45) -> list:
        """For each number, attach the NEAREST hint keyword within max_dist
        characters (avoids binding a number to a keyword in another clause)."""
        low = text.lower()
        hits = [((m.start() + m.end()) // 2, key)
                for pat, key in self.hints for m in pat.finditer(low)]
        claims = []
        for nm in NUM_RE.finditer(low):
            try:
                val = float(nm.group(1).replace(",", "")) * SCALE.get((nm.group(2) or "").lower(), 1)
            except ValueError:
                continue
            unit = None if nm.group(2) else self.unit_after.match(low, nm.end())
            # "750 ml" is a size → skip; but "14 kg per liter" / "14 kg/l" is a rate → check it
            if unit and not RATE_AFTER.match(low, unit.end()):
                continue
            npos = (nm.start() + nm.end()) // 2
            best, best_d = None, max_dist + 1
            for hpos, key in hits:
                d = abs(hpos - npos)
                if d >= best_d:
                    continue
                # magnitude guard: never bind to an anchor >100x off
                # (keeps "8 bottles" away from a 3,000,000-cases anchor)
                exp = self.facts.get(key, {}).get("value")
                if isinstance(exp, (int, float)) and exp and val:
                    if max(val, exp) / max(min(val, exp), 1e-9) > 100:
                        continue
                best, best_d = key, d
            if best is None:
                continue
            claims.append({"key": best, "claimed": val, "dist": best_d,
                           "snippet": text[max(0, nm.start() - 30): nm.end() + 30].strip()})
        claims.sort(key=lambda c: c["dist"])
        seen, uniq = set(), []
        for c in claims:
            sig = (c["key"], round(c["claimed"], 2))
            if sig not in seen:
                seen.add(sig)
                uniq.append(c)
        return uniq

    def check_text(self, text: str) -> dict:
        """Verdict for every numeric claim in `text`, plus a numeric accuracy score."""
        verdicts = [dict(self.cross_check(c["key"], c["claimed"]), snippet=c["snippet"])
                    for c in self.extract_claims(text)]
        counts = dict.fromkeys(STATUSES, 0)
        for v in verdicts:
            counts[v["status"]] += 1
        n = counts["CONFIRMED"] + counts["CLOSE"] + counts["DISPUTED"]
        acc = (counts["CONFIRMED"] + 0.5 * counts["CLOSE"]) / n if n else None
        return {"n_claims": len(verdicts), "counts": counts,
                "numeric_accuracy": round(acc, 2) if acc is not None else None,
                "verdicts": verdicts,
                "disputed": [v for v in verdicts if v["status"] == "DISPUTED"]}

    # ── prompt grounding ────────────────────────────────────────────────────
    def grounding(self, keys: Optional[Callable[[str], bool]] = None, max_facts: int = 40) -> str:
        lines = []
        for k, v in self.facts.items():
            if keys and not keys(k):
                continue
            val, unit = v["value"], v.get("unit", "")
            rng = ""
            if "lo" in v and "hi" in v and isinstance(val, (int, float)):
                rng = f" (range {v['lo']:,}–{v['hi']:,})"
            u = f" {unit}" if unit and not isinstance(val, str) else ""
            lines.append(f"- {k}: {val}{u}{rng} [{v.get('confidence', '')}, as of {v.get('as_of', '?')}]")
            if len(lines) >= max_facts:
                break
        return ("VERIFIED REFERENCE FACTS (curated ground truth — stay consistent with these "
                "ranges; flag if you must deviate):\n" + "\n".join(lines))
