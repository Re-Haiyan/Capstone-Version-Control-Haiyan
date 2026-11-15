# Guarded VM conclusions candidate — 15 November 2026

This branch is based on the VM's documented production SHA `2c6e056befe0ad7a24652bd12d4d28f7af236a8f`, not the older GitHub `deployment` tip. New product-specific explanation modules and front-end changes were selected from successful feature-CI commit `8e6860a97c948f55a1fe649826b104eb4318f125`.

Excluded: experimental XLM-RoBERTa sentiment models, all GPT-6/Claude research annotations, category revision pc5, shipped hazard/sentiment code and thresholds. Existing verdict and recommendation logic are unchanged. The product-specific feature is NOT independently human validated: its main feature evaluation is still F1 0.517 on Claude-assisted development review, and the original feature author recommends staging before production.

**First rollout keeps explanations OFF.** On the VM, before restart, create a systemd override setting `DEFAKETIVE_CONCLUSION_REASONS=0`. Once the production VM passes smoke tests and the team approves source accuracy, opt in to `=1` for a monitored pilot. The CI runs type checks, backend regression, build, and checks that the deployed sentiment/hazard files remain byte-identical to the VM base.

A GitHub merge does not deploy to the Azure VM. An authenticated SSH session is required for actual VM commands; no VM SSH key or Azure control connector is available to this ChatGPT session. Do not paste secrets into chat. See `deploy/vm-guarded-update.sh` for a guarded on-VM update that verifies production SHA, backs up the databases, enables the off-switch, fast-forwards to reviewed `deployment`, and restarts only after safety checks. If any preflight fails, stop and reconcile rather than forcing a reset.

The deployed service must be tested on actual VM after the update; GitHub Actions success is NOT evidence that the Azure VM changed or that the new conclusions are accurate.
