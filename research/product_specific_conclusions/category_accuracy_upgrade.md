# Category accuracy and profile separation (development)

Branch: feature/category-accuracy-20261115

Status: experimental. No merge or deployment; no new measured category accuracy, sentiment F1, or product-aspect F1.

## Changes

- Keeps the existing 49-category, 11-group taxonomy. Prioritizes specific product-head matches for toy cars, lipstick/makeup, haircare, serums/skincare, and whey/protein supplements over generic matching such as "car", "cup", or "collagen". Searches the main product head only so a bundled accessory after "with" cannot override it.
- Bumps the category rules revision to pc5 so reports can be reanalyzed when the change is eventually integrated.
- Separates bags and home textiles from clothing sizing rules. Bags gain narrowly worded experimental storage and zipper aspects; home textiles retain fabric aspects. Supplements use taste, expiry and overall quality, without importing snack-freshness or build-durability rules.
- Prevents obviously unrelated profile inheritance: automotive does not automatically use motorcycle aspects; cables and battery/solar products do not automatically use powerbank features; kitchen/dining and TV products do not automatically use small-appliance aspects. General evidence-grounded rules remain the fallback.
- Adds an "Auto-detected category" entry to the report details. Unknown categories appear as "Unclassified"; old reports without this backend field show "Not recorded (older report)" rather than a guessed value.
- Adds synthetic regression cases and profile mapping tests. The original locked 150-review feature evaluation and 80-claim evaluation remain untouched.

## Executed validation on the isolated branch

Latest checked commit: `be13af3cdbb4aaab9f4e8937bbf7071a06c10167`.

- GitHub Actions: all four jobs passed — Python 3.11: **407 tests, 8 skipped, 0 failed**; Python 3.12: **407 tests, 8 skipped, 0 failed**; Svelte check/build passed; saved-review audit passed.
- The repository's **15 documented previously problematic real listing titles**: correct category assignment went from **6/15** at original commit `a5ea4de` to **15/15** with pc5. These are known development examples and **not** an independent accuracy estimate. Every old-to-new title change is recorded in the downloadable GitHub Actions audit artifact.
- **182 genuine saved products**: 0 category changes in the comparison. All sampled reviews were from the existing development saved pool, with up to 30 written reviews per product.
- **46/182 product aspect snapshots changed**: 45 charger/cable products now use the narrower charger profile, 1 automotive product uses general instead of motorcycle. Across the sampled reviews, 6 inappropriate capacity claims from 4 charging accessories and 1 durability claim from the generic automotive product disappeared. Charging/overheating evidence was preserved for charger/cable products.
- Saved sentiment and verdict **snapshots** remain identical, because this audit did not re-run those models. This **does not prove** live hazard/verdict invariance after re-scanning; category changes on other product types may affect the hazard checker.
- Frontend job used a temporary npm install with `--no-package-lock` because the pre-existing `package-lock.json` and `package.json` are out of sync. This did not modify the committed lockfile.
- Neither the locked 150-review feature evaluation nor the 80-claim evaluation was used for tuning or rescored.

The PR also targets a feature branch being edited by a separate Claude Code session. Its newest backend aspect and extractor changes require a **combined-branch CI validation** before this patch is merged. Do not overwrite Claude's newer work.

## Validation required before integration

1. Run the full Python suite: python -m unittest discover -s tests -p "test_*.py"
2. Run frontend typecheck/build: npm run check and npm run build. Verify mobile and desktop rendering.
3. Recheck real development scans, including all previously misclassified listings, and report category confusion counts and new regressions.
4. Compare hazard tags, sentiment labels, product decisions, and safety warnings on the 182 saved products before and after pc5. No unchanged-decision claim is made until this runs.
5. Evaluate bag, bedding, and supplement aspects on genuinely fresh review samples, preserving the locked 150-review/80-claim reference sets.
6. Resolve conflicts with ongoing Claude Code work via a reviewed integration branch. Never automatically merge into deployment or main.
7. Stage and benchmark separately before any production deployment.

## Scope and limitations

This is category detection, profile mapping and transparent UI only. It does not make XLM-RoBERTa sentiment itself category-conditioned and does not change sentiment model weights or hazard thresholds.

The added cases are synthetic, not a measured accuracy improvement. New aspect profiles are experimental pending genuine new-review validation.
