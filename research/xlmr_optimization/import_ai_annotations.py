"""Validate and record AI-assisted annotations returned for a prepared sheet. It labels nothing: it checks what the annotator returned and logs the provenance as STATED by the submitter.

    python research/xlmr_optimization/import_ai_annotations.py <returned.csv> --sheet annotation/dev_pool_sheet.csv --model "ChatGPT <exact model/version>" --prompt annotation/chatgpt_prompt_policy_v1.md --submitted-by "<name>" --date 2026-11-16 [--batch dev_pool_batch_01]

The returned file has columns id,sentiment,tags,positive_aspect,negative_aspect,confidence,rationale (several returned batch files may be merged by repeating the call; every call is
logged). Checks: every id belongs to the sheet and appears once; values and policy-v1 rules (the same checks as sentiment_agreement.py); the review text is taken from the sheet by id
(never from the returned file). Output: annotation/ai_labelled/<sheet name>_ai_v1.csv (the sheet's columns plus labels, merged by id; existing labels are never overwritten; a second
import of an id is refused) and a line in annotation/ai_annotation_log.csv (UTC time, sheet, rows, SHA-256 of the returned file and of the prompt, model as stated, submitter, date).
The log records that the submitter STATES the rows were processed by that model; the repository cannot verify it. Original sheets are not modified.
"""
import csv, datetime, hashlib, os, pathlib, sys

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import sentiment_agreement as sa  # noqa: E402

ANN = pathlib.Path(os.environ.get("AI_ANNOTATION_DIR") or X / "annotation")  # AI_ANNOTATION_DIR: another folder (tests)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    args = sys.argv[1:]
    opt = {a: args[i + 1] for i, a in enumerate(args) if a.startswith("--")}
    returned = pathlib.Path(args[0])
    sheet = pathlib.Path(opt["--sheet"])
    for need in ("--model", "--prompt", "--submitted-by", "--date"):
        if need not in opt:
            sys.exit(f"{need} is required: the provenance of AI-assisted labels must be recorded as stated by the submitter.")
    base = list(csv.DictReader(open(sheet, encoding="utf-8-sig")))
    by_id = {r["id"]: r for r in base}
    got = list(csv.DictReader(open(returned, encoding="utf-8-sig")))
    problems, seen = [], set()
    for r in got:
        i = r.get("id", "")
        if i not in by_id:
            problems.append(f"{i}: not in the sheet"); continue
        if i in seen:
            problems.append(f"{i}: appears twice in the returned file"); continue
        seen.add(i)
        row = {**by_id[i], **{k: r.get(k, "") for k in ("sentiment", "tags", "positive_aspect", "negative_aspect", "confidence", "rationale")}}
        problems += sa.row_problems(row)
    out = ANN / "ai_labelled" / (sheet.stem + "_ai_v1.csv")
    done = {r["id"] for r in csv.DictReader(open(out, encoding="utf-8-sig"))} if out.exists() else set()
    for i in seen & done:
        problems.append(f"{i}: already labelled in {out.name}; originals are never overwritten")
    print(f"{len(got)} returned rows, {len(seen)} distinct, {len(problems)} problems")
    for p in problems[:40]:
        print("  ", p)
    if problems:
        sys.exit(1)
    out.parent.mkdir(parents=True, exist_ok=True)
    new = not out.exists()
    with open(out, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(base[0]))
        if new:
            w.writeheader()
        for r in got:
            w.writerow({**by_id[r["id"]], **{k: r.get(k, "") for k in ("sentiment", "tags", "positive_aspect", "negative_aspect", "confidence", "rationale")}})
    log = ANN / "ai_annotation_log.csv"
    first = not log.exists()
    with open(log, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if first:
            w.writerow(["utc_time", "sheet", "batch", "rows", "returned_sha256", "prompt_sha256", "model_as_stated_by_submitter", "submitted_by", "date_stated", "note"])
        w.writerow([datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), sheet.name, opt.get("--batch", ""), len(got), sha(returned), sha(opt["--prompt"]), opt["--model"], opt["--submitted-by"], opt["--date"],
                    "AI-assisted labels as stated by the submitter; not verified by the repository"])
    print("merged into", out, "and logged")


if __name__ == "__main__":
    main()
