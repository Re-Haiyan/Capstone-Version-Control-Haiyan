import assert from 'node:assert/strict';
import { test } from 'node:test';
import { api, ApiError, json } from '../../src/lib/api.ts';

test('sends credentials and JSON, and keeps the server response', async (t) => {
	const payload = { job: { id: 'job1' } };
	t.mock.method(globalThis, 'fetch', async (url, request) => {
		assert.equal(url, '/api/search');
		assert.equal(request.credentials, 'same-origin');
		assert.equal(request.method, 'POST');
		assert.equal(request.headers['Content-Type'], 'application/json');
		assert.deepEqual(JSON.parse(request.body), { query: 'product' });
		return Response.json(payload);
	});
	assert.deepEqual(await api('/api/search', json('POST', { query: 'product' })), payload);
});

test('preserves server validation messages and metadata', async (t) => {
	const body = { error: 'No free scans left today.', limit_reached: true };
	t.mock.method(globalThis, 'fetch', async () => Response.json(body, { status: 429 }));
	await assert.rejects(api('/api/search'), (error) => {
		assert.ok(error instanceof ApiError);
		assert.equal(error.status, 429);
		assert.equal(error.message, body.error);
		assert.deepEqual(error.body, body);
		return true;
	});
});

test('a gateway HTML response gives a readable error with its HTTP status', async (t) => {
	t.mock.method(globalThis, 'fetch', async () => new Response('<h1>Bad Gateway</h1>', { status: 502 }));
	await assert.rejects(api('/api/auth/me'), (error) => error.status === 502 && /temporarily unavailable/.test(error.message));
});

for (const body of ['<html>Login page</html>', 'null', '"unexpected text"']) {
	test(`an invalid successful response is an error: ${body}`, async (t) => {
		t.mock.method(globalThis, 'fetch', async () => new Response(body));
		await assert.rejects(api('/api/auth/me'), (error) => error.status === 502 && /unreadable response/.test(error.message));
	});
}

test('a network failure is identifiable as unavailable, preserving signed-in state', async (t) => {
	t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('Failed to fetch'); });
	await assert.rejects(api('/api/auth/me'), (error) => error instanceof ApiError && error.status >= 500 && /connection/.test(error.message));
});

test('times out a stalled request without repeating a POST', async (t) => {
	t.mock.timers.enable({ apis: ['setTimeout'] });
	const fetch = t.mock.method(globalThis, 'fetch', (_url, request) => new Promise((_resolve, reject) => {
		request.signal.addEventListener('abort', () => reject(request.signal.reason), { once: true });
	}));
	const pending = api('/api/search', { ...json('POST'), timeoutMs: 25 });
	t.mock.timers.tick(25);
	await assert.rejects(pending, (error) => error.status === 503 && /may still be processing/.test(error.message));
	assert.equal(fetch.mock.callCount(), 1);
});

test('the timeout also covers reading a stalled response body', async (t) => {
	t.mock.timers.enable({ apis: ['setTimeout'] });
	t.mock.method(globalThis, 'fetch', async (_url, request) => ({
		ok: true,
		json: () => new Promise((_resolve, reject) => {
			request.signal.addEventListener('abort', () => reject(request.signal.reason), { once: true });
		})
	}));
	const pending = api('/api/products', { timeoutMs: 25 });
	await Promise.resolve();
	t.mock.timers.tick(25);
	await assert.rejects(pending, (error) => error.status === 503);
});

test('caller cancellation is preserved and an already canceled request never starts', async (t) => {
	const controller = new AbortController();
	const reason = new DOMException('Canceled by caller', 'AbortError');
	const fetch = t.mock.method(globalThis, 'fetch', (_url, request) => new Promise((_resolve, reject) => {
		request.signal.addEventListener('abort', () => reject(request.signal.reason), { once: true });
	}));
	const pending = api('/api/products', { signal: controller.signal });
	controller.abort(reason);
	await assert.rejects(pending, (error) => error === reason);
	await assert.rejects(api('/api/products', { signal: controller.signal }), (error) => error === reason);
	assert.equal(fetch.mock.callCount(), 1);
});

test('cleans up the deadline after a successful response', async (t) => {
	t.mock.timers.enable({ apis: ['setTimeout'] });
	let signal;
	t.mock.method(globalThis, 'fetch', async (_url, request) => {
		signal = request.signal;
		return Response.json({ products: [] });
	});
	await api('/api/products');
	t.mock.timers.tick(60_000);
	assert.equal(signal.aborted, false);
});
