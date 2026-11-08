# Haiyan: scan usability and reliability improvements

This update is based on the `update-ui-ux` branch of DeFaketive and retains its
research model, evidence badges, plain-language verdicts, and recommendation rules.

## Research alignment

The supplied manuscript, **DeFaketive: A Counterfeit and Defective Product Detection
Using Sentiment Analysis with Recommendation System**
(`Group4_Caballero-et-al_DA.docx`), describes a review-based decision-support system.
Its specific objectives 4 and 5 concern presenting results clearly and evaluating
usability; Chapter 5, recommendation 8 calls for reducing interface complexity.

This iteration addresses those goals through recovery actions on the screen where
a shopper encounters a problem. It does not change hazard thresholds, train a new
model, introduce an aggregate risk score, or claim improved model accuracy or new
SUS/UMUX results. The manuscript itself is not included in the repository.

## What changes for a shopper

- A request that stalls stops waiting after 30 seconds and explains what happened.
  Cancellation still works, and requests are never automatically resubmitted.
- Invalid successful responses are treated as server errors rather than empty
  data. Gateway failures and connection problems have readable messages.
- If scan progress is interrupted, **Reconnect to scan** appears directly on
  both the guest and signed-in Analyze screens. It reads the original job, uses
  no additional free scan, and remains available after a page reload.
- If the server no longer has the job, the form unlocks and suggests checking
  saved reports before starting again.
- Signing out clears scheduled polling and ignores late scan-start and progress
  responses so an old scan cannot repopulate the next person's screen.
- Guest validation hints are associated with the product-link input. Unsupported
  marketplace links are marked invalid consistently, and the elapsed-time clock
  no longer changes live announcements or the header button's accessible name
  every second.

## Verification

With Node.js 24 and project dependencies installed:

```sh
npm run test:unit
npm run check
npm run test:extension
npm run build
npm run admin:build
```

The unit tests exercise HTTP failure handling and the actual rune-compiled scan
store with controlled responses, including interrupted scans, reloads, duplicate
submission prevention, sign-out races, and expired jobs. They do not require a
marketplace account, live scraping, the model files, or a production database.

Before wider release, verify the guest and signed-in flows with a keyboard and
screen reader at mobile and desktop widths. Test connection loss during an
active scan, reconnect after recovery, and a server restart. A follow-up usability
study should record the tasks performed and collect fresh SUS/UMUX responses as
recommended by the manuscript; passing software tests is not a new usability score.
