"""triple-check "question"            ask the tequila cell (2 experts + verifier)
triple-check verify "some text"      fact-check text against the fact base
triple-check calc 4000000            agave→bottle supply chain for N cases/yr
triple-check facts [term]            show / search the fact base"""

import argparse
import json
import sys

from .cell import format_report, format_verification
from .domains import tequila


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmds = {"ask", "verify", "calc", "facts"}
    if argv and argv[0] not in cmds and argv[0] not in ("-h", "--help"):
        argv.insert(0, "ask")
    p = argparse.ArgumentParser(prog="triple-check", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--expert-model", default="qwen2.5:3b")
    p.add_argument("--verifier-model", default="llama3.2")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ask")
    a.add_argument("question", nargs="+")
    a.add_argument("--json", action="store_true", help="print the full result as JSON")
    v = sub.add_parser("verify")
    v.add_argument("text", nargs="+")
    v.add_argument("--no-llm", action="store_true", help="numeric check only, no second-opinion model")
    c = sub.add_parser("calc")
    c.add_argument("cases", type=float)
    c.add_argument("--density", type=float, help="plants per acre")
    f = sub.add_parser("facts")
    f.add_argument("term", nargs="*")
    args = p.parse_args(argv)

    cell = tequila.make_cell(args.expert_model, args.verifier_model)
    if args.cmd == "ask":
        r = cell.triple_check(" ".join(args.question), log=lambda m: print(f"  {m}", file=sys.stderr))
        print(json.dumps(r, indent=2) if args.json else format_report(r))
    elif args.cmd == "verify":
        print(format_verification(cell.verify(" ".join(args.text), second_opinion=not args.no_llm)))
    elif args.cmd == "calc":
        print(tequila.format_supply_chain(tequila.supply_chain(args.cases, density_per_acre=args.density)))
    else:
        term = " ".join(args.term).lower()
        for k, fact in tequila.FACTS.items():
            if term and term not in k.lower() and term not in str(fact).lower():
                continue
            rng = f" ({fact['lo']:,}–{fact['hi']:,})" if "lo" in fact else ""
            print(f"• {k}: {fact['value']}{rng} [{fact.get('confidence')}]\n    {fact.get('note', '')}")


if __name__ == "__main__":
    main()
