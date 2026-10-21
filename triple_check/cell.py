"""The Triple-Check Protocol.

    CHECK 0  calculators: math the question needs is done in PYTHON and handed
             to the experts as verified numbers. LLMs explain them, never compute them.
    CHECK 1  expert A answers, grounded in the fact base
    CHECK 2  expert B answers independently (cross-reference)
    CHECK 3  every number in both answers is scored against the fact base's ranges,
             and a verifier on a DIFFERENT model family gives a second opinion
             (so the third check isn't an echo of the experts)

Cell confidence = mean numeric accuracy of both experts; any DISPUTED claim
multiplies it by 0.6 and rules out HIGH.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from . import llm
from .facts import FactBase


@dataclass
class Expert:
    name: str
    persona: str                                   # system prompt
    model: str = "qwen2.5:3b"
    keywords: tuple = ()                           # routes a question to this expert
    fact_filter: Optional[Callable[[str], bool]] = None   # which facts ground this expert


@dataclass
class Cell:
    facts: FactBase
    experts: list                                   # exactly two Experts
    verifier_model: str = "llama3.2"                # different family from the experts
    calculators: list = field(default_factory=list) # [question -> verified block or ""]
    ask: Callable = llm.ask                         # injectable for tests

    def route(self, question: str) -> str:
        q = question.lower()
        scores = [sum(w in q for w in e.keywords) for e in self.experts]
        if scores[0] == scores[1]:
            return "both"
        return self.experts[scores.index(max(scores))].name

    def _expert_answer(self, e: Expert, question: str, max_tokens: int) -> str:
        prompt = (f"{self.facts.grounding(e.fact_filter)}\n\nQUESTION:\n{question}\n\n"
                  f"Answer as the {e.name} expert:")
        return self.ask(prompt, model=e.model, system=e.persona, max_tokens=max_tokens)

    def verify(self, text: str, second_opinion: bool = True) -> dict:
        rep = self.facts.check_text(text)
        rep["independent_note"] = ""
        if second_opinion and text.strip():
            vsum = "; ".join(f"{v['key']}={v['claimed']}→{v['status']}" for v in rep["verdicts"]) or "none"
            rep["independent_note"] = self.ask(
                f"{self.facts.grounding()}\n\nYou are an independent fact checker. Here is a claim/answer:\n"
                f'"""{text[:1200]}"""\n\nAutomated numeric check found: {vsum}\n\n'
                "Briefly (3-4 sentences): do the claims hold up against the reference facts? "
                "Call out anything misleading or any number outside the verified ranges.",
                model=self.verifier_model,
                system="You are a meticulous, skeptical fact checker. Be terse and specific. "
                       "Only flag genuine problems.",
                max_tokens=300)
        return rep

    @staticmethod
    def confidence(reports: list) -> tuple:
        accs = [r["numeric_accuracy"] for r in reports if r["numeric_accuracy"] is not None]
        disputed = sum(r["counts"]["DISPUTED"] for r in reports)
        if not accs:
            return "UNVERIFIED", 0.5
        score = sum(accs) / len(accs)
        if disputed:
            score *= 0.6
        if score >= 0.85 and not disputed:
            label = "HIGH"
        elif score >= 0.6:
            label = "MEDIUM"
        else:
            label = "LOW"
        return label, round(score, 2)

    def triple_check(self, question: str, max_tokens: int = 500, second_opinion: bool = True,
                     log: Callable = lambda msg: None) -> dict:
        route = self.route(question)
        verified = "\n\n".join(b for b in (c(question) for c in self.calculators) if b)
        q = question
        if verified:
            log("CHECK 0 — verified calculation injected")
            q += "\n\nUse THESE verified pre-computed numbers (do not recompute them):\n" + verified

        a, b = self.experts
        log(f"CHECK 1/3 — {a.name}")
        ans_a = self._expert_answer(a, q, max_tokens)
        log(f"CHECK 2/3 — {b.name}")
        ans_b = self._expert_answer(b, q, max_tokens)
        log("CHECK 3/3 — fact check + independent verifier")
        rep_a = self.verify(ans_a or "", second_opinion)
        rep_b = self.verify(ans_b or "", second_opinion)

        label, score = self.confidence([rep_a, rep_b])
        lead = ans_a if route == a.name else ans_b
        if verified:
            lead = verified + "\n\n" + (lead or "")    # the auditable numbers lead, not the prose
        disputed = rep_a["disputed"] + rep_b["disputed"]
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": question, "route": route,
            "confidence": label, "confidence_score": score,
            "verified_calculation": verified,
            "lead_answer": lead,
            "answers": {a.name: ans_a, b.name: ans_b},
            "verification": {a.name: rep_a, b.name: rep_b},
            "disputed_claims": disputed, "n_disputed": len(disputed),
        }


def format_report(r: dict) -> str:
    out = ["", "═" * 64, "  TRIPLE-CHECKED ANSWER", "═" * 64,
           f"  Q: {r['question']}",
           f"  Route: {r['route']}   Confidence: {r['confidence']} ({r['confidence_score']})"
           f"   Disputed: {r['n_disputed']}", "─" * 64,
           "  " + (r["lead_answer"] or "(local model unavailable)").replace("\n", "\n  ")]
    if r["n_disputed"]:
        out.append("\n  ⛔ FLAGGED CLAIMS (outside verified ranges):")
        for d in r["disputed_claims"]:
            out.append(f"    • {d['key']}: claimed {d['claimed']:,} vs expected {d['expected']:,} "
                       f"({d['lo']:,}–{d['hi']:,})  «{d['snippet']}»")
    accs = " | ".join(f"{k} acc={v['numeric_accuracy']}" for k, v in r["verification"].items())
    out.append(f"\n  Verification — {accs}")
    return "\n".join(out)


def format_verification(rep: dict) -> str:
    c = rep["counts"]
    out = [f"Claims checked: {rep['n_claims']}  (✅{c['CONFIRMED']} ~{c['CLOSE']} "
           f"⛔{c['DISPUTED']} ?{c['NO_ANCHOR']})   numeric accuracy: {rep['numeric_accuracy']}"]
    for v in rep["verdicts"]:
        exp = f" (expected {v['lo']:,}–{v['hi']:,})" if v.get("lo") is not None else ""
        out.append(f"  {v['status']:<9} {v['key']} = {v['claimed']:,}{exp}  «{v['snippet']}»")
    if rep.get("independent_note"):
        out += ["", "Independent reviewer:", rep["independent_note"]]
    return "\n".join(out)
