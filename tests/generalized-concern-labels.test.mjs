import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const read = (path) => readFileSync(new URL('../' + path, import.meta.url), 'utf8');
const product = read('src/lib/product.ts');
const conclusion = read('src/lib/components/report/verdict-block.svelte');
const checks = read('src/lib/components/report/checks-card.svelte');
const report = read('src/lib/components/report/report-view.svelte');

test('all five hazard identifiers have broader, non-accusatory presentation names', () => {
  for (const [category, name] of Object.entries({
    safety: 'Safety concerns',
    defect: 'Functionality or damage concerns',
    quality: 'Quality concerns',
    counterfeit: 'Authenticity concerns',
    not_as_described: 'Listing differences'
  })) {
    assert.match(product, new RegExp(category + ": '" + name + "'"));
  }
  assert.doesNotMatch(product, /['"]Faulty or broken['"]|['"]Possible fake['"]/);
});

test('all report surfaces normalize historic server labels without altering counts', () => {
  assert.match(product, /export const concernLabel =/);
  assert.match(product, /concernLabel\(category, view\(product\)\.labels/);
  assert.match(conclusion, /concernLabel\(badge\.category, badge\.label/);
  assert.match(conclusion, /Math\.max\(old\?\.reviews \?\? 0, reviews\)/);
  assert.match(checks, /concernLabel\(badge\.category, badge\.label\)/);
  assert.match(report, /concernLabel\(item\.category, item\.label\)/);
  assert.match(conclusion, /Common concerns/);
  assert.match(conclusion, /DeFaketive is not 100% accurate/);
});
