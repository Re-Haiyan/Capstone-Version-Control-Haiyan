/** A failed call to the Flask app. `body` keeps whatever else the server said. */
export class ApiError extends Error {
	status: number;
	body: Record<string, any>;
	constructor(message: string, status: number, body: Record<string, any>) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.body = body;
	}
}

export type ApiOptions = RequestInit & { timeoutMs?: number };

/** Fetch JSON with a bounded wait. Requests are never automatically repeated. */
export async function api<T = any>(url: string, options: ApiOptions = {}): Promise<T> {
	const { timeoutMs = 30_000, signal, ...request } = options;
	const controller = new AbortController();
	const cancel = () => controller.abort(signal?.reason);
	if (signal?.aborted) signal.throwIfAborted();
	signal?.addEventListener('abort', cancel, { once: true });
	let timedOut = false;
	const timer = setTimeout(() => {
		timedOut = true;
		controller.abort();
	}, timeoutMs);
	try {
		const response = await fetch(url, { credentials: 'same-origin', ...request, signal: controller.signal });
		let body: unknown;
		try {
			body = await response.json();
		} catch (error) {
			if (controller.signal.aborted) throw error;
			if (response.ok) throw new ApiError('The server returned an unreadable response. Please try again shortly.', 502, {});
		}
		const details = body && typeof body === 'object' && !Array.isArray(body) ? body as Record<string, any> : {};
		if (!response.ok) {
			const message = typeof details.error === 'string' && details.error.trim()
				? details.error
				: response.status >= 500
					? 'The server is temporarily unavailable. Please try again shortly.'
					: 'The request could not be completed. Please try again.';
			throw new ApiError(message, response.status, details);
		}
		if (!body || typeof body !== 'object') {
			throw new ApiError('The server returned an unreadable response. Please try again shortly.', 502, {});
		}
		return body as T;
	} catch (error) {
		if (signal?.aborted) throw signal.reason;
		if (timedOut) {
			throw new ApiError('The server took too long to respond. Your request may still be processing. Check its status before trying again.', 503, {});
		}
		if (error instanceof ApiError) throw error;
		throw new ApiError('Could not reach the server. Check your connection and try again.', 503, {});
	} finally {
		clearTimeout(timer);
		signal?.removeEventListener('abort', cancel);
	}
}

/** A JSON request. The server only accepts JSON for forms, which keeps other sites from posting to it. */
export const json = (method: string, body: unknown = {}): RequestInit => ({
	method,
	headers: { 'Content-Type': 'application/json' },
	body: JSON.stringify(body)
});
