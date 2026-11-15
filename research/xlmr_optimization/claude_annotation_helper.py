"""Records Claude's annotations of a blind batch compactly, then validates and imports them (the labels are the assistant's reading of each review; this tool only writes them down).

    python research/xlmr_optimization/claude_annotation_helper.py <batch number> "<spec>"  [show-next]
The assistant reads every review of the batch, then gives exceptions to the DEFAULT, which is applied to reviews it read and judged to be pure copied tag lists with no personal experience:
default = neutral, tag no-opinion, confidence high. Exceptions (space-separated ids after a code):
  P: positive   Pl: positive, low confidence   Ng: negative   Nl: neutral without tag, low   Nt: neutral no-opinion, low   U: unclear
  Dn: negative delivery-only   Dp: positive delivery-only
  X:id=positive aspect/negative aspect=label  : a mixed review (label positive, negative, or mixed when neither dominates), aspects as given
Example: "P: N0151 N0152; Ng: N0160; X:N0170=fast/slow=positive". Rows of the batch not covered by the default keep the default. Provenance: model and prompt are logged by import_ai_annotations.py as
'Claude (claude-sonnet-5-5) via Claude Code, not ChatGPT'. Sets: neutral_candidate_pool (batches neutral_candidates_batch_NN).
"""
import csv, pathlib, re, subprocess, sys

X = pathlib.Path(__file__).resolve().parent
A = X / "annotation"
HDR = ["id", "sentiment", "tags", "positive_aspect", "negative_aspect", "confidence", "rationale"]
CODES = {"P": ("positive", "", "high"), "Pl": ("positive", "", "low"), "Ng": ("negative", "", "high"), "Nl": ("neutral", "", "low"), "Nt": ("neutral", "no-opinion", "low"), "U": ("unclear", "", "high"),
         "Dn": ("negative", "delivery-only", "high"), "Dp": ("positive", "delivery-only", "high")}


def parse(spec):
    out = {}
    for part in [p.strip() for p in spec.split(";") if p.strip()]:
        if part.startswith("X:"):
            for m in re.finditer(r"(N\d{4})=([^=]*?)/([^=]*?)=(positive|negative|mixed)", part):
                i, pa, na, lab = m.groups()
                out[i] = (lab, "mixed", pa.strip(), na.strip(), "low", "mixed evaluation")
        else:
            code, ids = part.split(":", 1)
            lab, tags, conf = CODES[code.strip()]
            for i in ids.split():
                out[i] = (lab, tags, "", "", conf, "reviewed")
    return out


def show(n, width=170):
    for r in csv.DictReader(open(A / "chatgpt_batches" / f"neutral_candidates_batch_{n:02d}.csv", encoding="utf-8-sig")):
        print(r["id"], "|", r["product"][:18], "|", r["review_text"][:width].replace("\n", " "))


def main():
    n = int(sys.argv[1])
    spec = sys.argv[2]
    rows = list(csv.DictReader(open(A / "chatgpt_batches" / f"neutral_candidates_batch_{n:02d}.csv", encoding="utf-8-sig")))
    ex = parse(spec)
    unknown = set(ex) - {r["id"] for r in rows}
    if unknown:
        sys.exit(f"ids not in the batch: {sorted(unknown)}")
    target = A / "claude_returns" / f"neutral_candidates_batch_{n:02d}_returned.csv"
    with open(target, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(HDR)
        for r in rows:
            w.writerow([r["id"], *ex.get(r["id"], ("neutral", "no-opinion", "", "", "high", "copied tag list without personal experience"))])
    cmd = [sys.executable, str(X / "import_ai_annotations.py"), str(target), "--sheet", str(A / "neutral_candidate_pool.csv"), "--model", "Claude (claude-sonnet-5-5) via Claude Code; labelled directly by the assistant in-session; NOT ChatGPT",
           "--prompt", str(A / "chatgpt_prompt_policy_v1.md"), "--submitted-by", "Claude Code assistant, at the owner's request", "--date", "2026-11-15", "--batch", f"neutral_candidates_batch_{n:02d}"]
    done = subprocess.run(cmd, capture_output=True, text=True)
    print(done.stdout.strip().splitlines()[0] if done.stdout else done.stderr[-300:], "| exceptions:", len(ex))
    if done.returncode:
        print(done.stdout[-600:], done.stderr[-300:])
        sys.exit(1)
    if len(sys.argv) > 3:
        show(int(sys.argv[3]))


if __name__ == "__main__":
    if len(sys.argv) == 2:
        show(int(sys.argv[1]))
    else:
        main()
