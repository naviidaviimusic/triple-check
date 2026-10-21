# triple-check

**Small local LLMs are confident and bad at arithmetic.** Ask a 3B model how much
land a tequila brand needs and it will tell you a 9-litre case holds 36 litres.

`triple-check` is a pattern (and a small library) for making local-model answers
trustworthy enough to act on:

1. **Python does the math.** Calculations come from verified constants, computed in code,
   and the models are told to *explain* those numbers, not produce their own.
2. **Two experts answer independently**, both grounded in a curated fact base.
3. **Every number in both answers is checked** against the fact base's ranges, and a
   verifier from a **different model family** gives a second opinion, so the third
   check isn't an echo of the first two.

Runs fully offline on [Ollama](https://ollama.com). Zero dependencies.

## Example: the tequila cell

The bundled domain is a tequila agronomy + business cell: 29 curated facts (18 numeric
ranges), an agave→bottle supply-chain calculator, an agronomist and an industry analyst.

```console
$ triple-check verify --no-llm "Agave matures in 7 years, gives 8 bottles per plant, and it takes 14 kg/l."
Claims checked: 3  (✅2 ~0 ⛔1 ?0)   numeric accuracy: 0.67
  CONFIRMED maturity_years = 7.0 (expected 6.0–8.0)
  DISPUTED  agave_kg_per_liter = 14.0 (expected 6.0–8.0)  «it takes 14 kg/l.»
  CONFIRMED bottles_per_plant = 8.0 (expected 7.0–10.0)

$ triple-check "How many acres would we need to match Don Julio's volume?"
  CHECK 0 — verified calculation injected
  CHECK 1/3 — farming
  CHECK 2/3 — business
  CHECK 3/3 — fact check + independent verifier
  [Don Julio: 3,300,000 9L cases/yr]
  VERIFIED CALCULATION (computed in Python from the fact base — not estimated):
    • 3,300,000 cases/yr × 9 L = 29,700,000 L/yr = 39,600,000 bottles/yr
    • Agave milled: 207,900 tonnes/yr (at 7.0 kg/L)
    • Plants harvested: 4,950,000/yr (at 6.0 L/plant)
    • Land harvested: 4,125 acres/yr (at 1,200 plants/acre)
    • STANDING ACREAGE in production: 28,875 acres (× 7-yr maturity)
  … then both experts' explanations, each number verified …
```

In testing, this caught a business-analyst model claiming a 9 L case = "36 liters" and
"14 kg/L", flagged 6 disputed claims, and dropped the answer's confidence to 0.42
instead of passing it along.

## Verdicts

| Claim verdict | Meaning |
|---|---|
| `CONFIRMED` | inside the fact's `[lo, hi]` range |
| `CLOSE` | outside the range but within 30% of the central value |
| `DISPUTED` | further off: **flagged**, never silently passed |
| `NO_ANCHOR` | nothing numeric to check against: treated as opinion |

**Cell confidence** is the mean numeric accuracy of both experts. Any disputed claim
multiplies it by 0.6 and rules out `HIGH` (≥ 0.85). `MEDIUM` ≥ 0.6, else `LOW`.

## How claims are found

For every number in an answer, the checker binds it to the **nearest** keyword hint
(within 45 characters) that points at a fact, so a number isn't matched to a keyword
from another clause. Guards:

- **Magnitude guard:** a number is never bound to a fact more than 100× away ("8 bottles" is never checked against "3,000,000 cases")
- **Sizes vs rates:** "750 ml" and "5,000 acres" are sizes and are skipped. "14 kg per liter" and "7 kg/l" are rates and are checked
- **Scale words:** "4 million cases" → 4,000,000. Single letters ("4m") are ignored as too ambiguous

## Use your own domain

```python
from triple_check import Cell, Expert, FactBase

FACTS = {
    "max_dose_mg": {"value": 4000, "unit": "mg/day", "lo": 3000, "hi": 4000,
                    "confidence": "HIGH", "as_of": 2024, "note": "adult acetaminophen ceiling"},
}
HINTS = [(r"per\s+day|daily|a\s+day", "max_dose_mg")]

def dose_calculator(question: str) -> str:
    return ""            # return a VERIFIED CALCULATION block when the question needs math

cell = Cell(
    FactBase(FACTS, HINTS),
    experts=[Expert("clinical", "You are a pharmacist...", "qwen2.5:3b", ("dose", "mg")),
             Expert("safety", "You are a toxicologist...", "qwen2.5:3b", ("risk", "liver"))],
    verifier_model="llama3.2",
    calculators=[dose_calculator],
)
result = cell.triple_check("Is 6000 mg a day safe?")
print(result["confidence"], result["disputed_claims"])
```

See [`triple_check/domains/tequila.py`](triple_check/domains/tequila.py) for a complete domain.

## Install

```bash
pip install git+https://github.com/naviidaviimusic/triple-check
ollama pull qwen2.5:3b && ollama pull llama3.2
```

```
triple-check "question"                    ask the cell
triple-check verify [--no-llm] "text"      fact-check any text
triple-check calc 4000000 [--density N]    supply chain for N 9-L cases/yr
triple-check facts [term]                  browse the fact base
```

## Honesty note

The tequila figures are curated estimates from public industry knowledge (CRT,
Diageo/Bacardi/Becle disclosures, trade press). Each one carries a confidence level
and an as-of year. They're honest ballparks, not live data. Update them in one place,
the fact base, and never hard-code them in prompts.

## License

MIT © Victor Navejar ([Navii](https://github.com/naviidaviimusic))
