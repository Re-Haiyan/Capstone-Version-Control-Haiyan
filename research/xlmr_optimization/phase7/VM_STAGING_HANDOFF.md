# Phase 7 VM staging handoff (do NOT activate live)

The user wants Phase 7 installed on the existing Azure VM. Only GitHub repository and CI were accessible from this ChatGPT environment: no authenticated VM console or SSH session is available.

## Files prepared

- Research branch: research/phase7-staging-export-20261116.
- Training source: GitHub Actions run 43734828440.
- Staging converter: research/xlmr_optimization/phase7/export_staging_onnx.py.
- Staging workflow: .github/workflows/phase7-stage-onnx-candidate.yml.
- Output artifact: phase7-onnx-research-staging-only.
- VM read-only check: deploy/phase7-readonly-vm-check.sh.
- Staging artifact contains only ONNX weights, tokenizer, research-only manifest and CPU diagnostics. No customer review text.

## Why not to overwrite the production model yet

1. The production model loader validates SHA-256 and requires qualified_for_integration true. Research candidate is intentionally marked false. Do not bypass or forge this release gate.
2. The current hazard v6 manifest pins the old sentiment ONNX SHA. The defect scorer uses sentiment predictions as a gate. Swapping to the new model without recalibration raises LearnedModelError or changes hazard behavior. Simply editing the expected hash would not make the existing thresholds valid.
3. Existing ONNX model is about 95 MB. The new staging INT8 model is about 266 MB, which may exceed a small VM's available physical memory once the running application is included.
4. Previous scores reflect AI-assisted labels and a tiny non-independent sample. No human-verified product-disjoint final evaluation has qualified Phase 7, and natural Filipino/Taglish neutral performance is weakly measured.
5. Any final release requires product-specific conclusions, hazard regression, app integration and rollback checks.

## Work on the ACTUAL VM using authorized SSH

Check original service without modifying it:

    sudo systemctl is-active defaketive
    git rev-parse HEAD
    free -m
    df -h .
    sudo journalctl -u defaketive -n 30 --no-pager

Download the successful Phase 7 staging artifact from GitHub Actions using GitHub UI or an authenticated GH CLI into a PRIVATE directory outside the live checkout. Never include GitHub tokens in repository files or logs. Never copy any of these files into the production sentiment_onnx directory.

With the staging artifact extracted to a private path:

    bash deploy/phase7-readonly-vm-check.sh "$HOME/phase7-staging"

The read-only checker verifies file SHA-256, the current hazard dependency, size and VM memory. It does not restart the service, load a second model, modify any config or write to the database. Record the output and halt if the checker reports a mismatch or memory concern.

## Real deployment blockers

- Lock the trained model and obtain an independent human-adjudicated product-ID-disjoint evaluation with macro-F1 >= 0.80, including meaningful Filipino/Taglish natural Neutral examples.
- Verify PyTorch-vs-ONNX correctness and measure isolated memory plus live-VM memory under realistic traffic.
- Correctly recalibrate and test the hazard sentiment gate (or implement verified dual-model separation with sufficient memory).
- Test product-specific conclusions and cached/saved analysis invalidation.
- Snapshot model and DB, preconfigure automatic rollback, then release using a canary and health gates.

No live VM changes have been performed by this handoff.
