import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';
import { beforeEach, test } from 'node:test';
import { compileModule } from 'svelte/compiler';
import { ApiError } from '../../src/lib/api.ts';

// Run the actual rune-compiled store with controlled server responses and browser services.
const dataModule = (source) => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const proxy = (name) => `export const ${name} = new Proxy({}, { get: (_target, key) => globalThis.__scanHarness.${name}[key] });`;
const mocks = {
	'$app/navigation': dataModule('export const goto = (...args) => globalThis.__scanHarness.goto(...args);'),
	'$app/state': dataModule(proxy('page')),
	'svelte-sonner': dataModule(proxy('toast')),
	'#lib/api.js': dataModule(`export { ApiError, json } from ${JSON.stringify(new URL('../../src/lib/api.ts', import.meta.url).href)}; export const api = (...args) => globalThis.__scanHarness.api(...args);`),
	'#lib/product.js': new URL('../../src/lib/product.ts', import.meta.url).href,
	'#lib/nav.js': dataModule('export const reportHrefFor = (link) => `/app/report?link=${encodeURIComponent(link)}`;')
};
for (const name of ['auth', 'catalog', 'library', 'prefs', 'ui']) {
	mocks[`./${name}.svelte.js`] = dataModule(proxy(name));
}
const source = readFileSync(new URL('../../src/lib/stores/scan.svelte.ts', import.meta.url), 'utf8');
const { js } = compileModule(stripTypeScriptTypes(`${source}\nexport { Scan };`), { filename: 'scan.svelte.js' });
const compiled = js.code.replace(/from (['"])([^'"]+)\1/g, (_match, _quote, specifier) => {
	const target = mocks[specifier] ?? import.meta.resolve(specifier);
	return `from ${JSON.stringify(target)}`;
});
const { Scan } = await import(dataModule(compiled));
const LINK = 'https://www.lazada.com.ph/products/test-i111-s222.html';
const options = { query: LINK, marketplace: 'lazada', live: true, productCount: 1, reviewCount: 100 };
const job = { id: 'job1', state: 'running', query: LINK, platform: 'lazada', created_at: new Date().toISOString() };
const flush = () => new Promise(setImmediate);
let store;
let requests;

beforeEach((t) => {
	t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
	requests = [];
	const saved = new Map();
	Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: {
		getItem: (key) => saved.get(key) ?? null,
		setItem: (key, value) => saved.set(key, value),
		removeItem: (key) => saved.delete(key)
	} });
	globalThis.__scanHarness = {
		api: async (url, request) => {
			requests.push({ url, method: request?.method ?? 'GET' });
			return url === '/api/search' ? { job } : { ...job };
		},
		page: { url: new URL('http://localhost/scan') },
		goto: async () => {},
		toast: { warning() {}, success() {} },
		auth: { user: null, apply() {} },
		catalog: { lookup() {}, browse: [], products: [], all: [], load: async () => {}, loadAll: async () => {} },
		library: { mine: [], recordScan() {} },
		prefs: { notify() {} },
		ui: { openAuth() {} }
	};
	store = new Scan();
	t.after(() => { store.reset(); delete globalThis.sessionStorage; });
});

test('reconnects to the same job after a lost connection without charging another scan', async () => {
	const original = globalThis.__scanHarness.api;
	let disconnected = true;
	globalThis.__scanHarness.api = async (url, request) => {
		const result = await original(url, request);
		if (url.startsWith('/api/jobs/') && disconnected) throw new Error('Connection lost.');
		return result;
	};
	await store.search(options);
	await flush();
	assert.equal(store.summary.state, 'attention');
	assert.equal(store.busy, true);
	assert.match(store.feedback.message, /without starting another scan/);
	await store.search(options);
	assert.equal(requests.filter((r) => r.method === 'POST').length, 1);
	disconnected = false;
	await store.reconnect();
	assert.equal(store.summary.state, 'running');
	assert.equal(store.summary.id, job.id);
	assert.equal(store.feedback, null);
	assert.equal(requests.filter((r) => r.method === 'POST').length, 1);
	assert.equal(requests.filter((r) => r.url === '/api/jobs/job1').length, 2);
});

test('an interrupted scan remains recoverable after a reload', async () => {
	sessionStorage.setItem('defaketive-home-scan', JSON.stringify({ ...job, state: 'attention', message: 'Connection lost.' }));
	store.restore();
	assert.equal(store.busy, true);
	assert.equal(store.feedback.title, 'Scan connection interrupted');
	await store.reconnect();
	assert.equal(store.summary.state, 'running');
	assert.deepEqual(requests.map((r) => r.method), ['GET']);
});

test('reset cancels a scheduled poll so signing out sends no stale job requests', async (t) => {
	await store.search(options);
	await flush();
	assert.equal(requests.length, 2);
	store.reset();
	t.mock.timers.tick(10_000);
	await flush();
	assert.equal(requests.length, 2);
	assert.equal(store.summary, null);
	assert.equal(store.busy, false);
});

test('reset ignores a scan-start response that arrives after signing out', async () => {
	let finish;
	globalThis.__scanHarness.api = () => new Promise((resolve) => { finish = resolve; });
	const pending = store.search(options);
	store.reset();
	finish({ job });
	await pending;
	assert.equal(store.summary, null);
	assert.equal(store.busy, false);
});

test('reset ignores an in-flight progress response', async () => {
	const original = globalThis.__scanHarness.api;
	let finish;
	globalThis.__scanHarness.api = (url, request) => url.startsWith('/api/jobs/')
		? new Promise((resolve) => { finish = resolve; })
		: original(url, request);
	await store.search(options);
	store.reset();
	finish({ ...job, state: 'complete' });
	await flush();
	assert.equal(store.summary, null);
	assert.equal(store.feedback, null);
});

test('reset ignores a browser-extension check that arrives after signing out', async () => {
	let finish;
	globalThis.__scanHarness.api = () => new Promise((resolve) => { finish = resolve; });
	const pending = store.submitCollected({ link: LINK });
	store.reset();
	finish({ job });
	assert.match((await pending).failure, /interrupted/);
	assert.equal(store.summary, null);
	assert.equal(store.busy, false);
});

test('a malformed job response offers recovery instead of pretending to make progress', async () => {
	const original = globalThis.__scanHarness.api;
	globalThis.__scanHarness.api = (url, request) => url.startsWith('/api/jobs/') ? {} : original(url, request);
	await store.search(options);
	await flush();
	assert.equal(store.summary.state, 'attention');
	assert.match(store.feedback.message, /unreadable scan status/);
});

test('a reconnected job that failed unlocks the form and preserves its explanation', async () => {
	sessionStorage.setItem('defaketive-home-scan', JSON.stringify({ ...job, state: 'attention' }));
	store.restore();
	globalThis.__scanHarness.api = async () => ({ ...job, state: 'error', message: 'The marketplace stopped this scan.' });
	await store.reconnect();
	assert.equal(store.busy, false);
	assert.equal(store.summary.state, 'error');
	assert.equal(store.feedback.message, 'The marketplace stopped this scan.');
});

test('a job lost after a server restart unlocks the form instead of trapping the shopper', async () => {
	sessionStorage.setItem('defaketive-home-scan', JSON.stringify({ ...job, state: 'attention' }));
	store.restore();
	globalThis.__scanHarness.api = async () => { throw new ApiError('That collection job no longer exists.', 404, {}); };
	await store.reconnect();
	assert.equal(store.busy, false);
	assert.equal(store.summary.state, 'error');
	assert.match(store.feedback.message, /Check your saved reports/);
});
