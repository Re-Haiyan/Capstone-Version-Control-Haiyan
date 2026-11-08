/** A failed call to the Flask app. `body` keeps whatever else the server said. */
export class ApiError extends Error {
	status: number;
	body: Record<string, any>;
	constructor(message: string, status: number, body: Record<string, any>) {
		super(message);
		this.status = status;
		this.body = body;
	}
}

/** Keep a failed request from leaving a screen stuck in its loading state forever. */
export const API_TIMEOUT_MS = 30_000;

const NETWORK_ERROR = "Couldn't reach DeFaketive. Check that the server is running and try again.";
const TIMEOUT_ERROR = 'The server took too long to respond. Check your connection and try again.';
const INVALID_RESPONSE_ERROR = 'The server returned an invalid response. Please try again.';

/** Fetch JSON from the Flask app. Throws an ApiError carrying a readable failure. */
export async function api<T = any>(url: string, options: RequestInit = {}): Promise<T> {
	const controller = new AbortController();
	const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
	const externalSignal = options.signal;
	const abortFromCaller = () => controller.abort();
	externalSignal?.addEventListener('abort', abortFromCaller, { once: true });

	let response: Response;
	try {
		response = await fetch(url, { credentials: 'same-origin', ...options, signal: controller.signal });
	} catch (error) {
		if (externalSignal?.aborted) throw error;
		if (error instanceof DOMException && error.name === 'AbortError') {
			throw new ApiError(TIMEOUT_ERROR, 408, { timeout: true });
		}
		throw new ApiError(NETWORK_ERROR, 0, { network: true });
	} finally {
		clearTimeout(timeout);
		externalSignal?.removeEventListener('abort', abortFromCaller);
	}

	const body = await response.json().catch(() => null);
	if (!body || typeof body !== 'object' || Array.isArray(body)) {
		throw new ApiError(INVALID_RESPONSE_ERROR, 502, { invalid_response: true });
	}
	if (!response.ok) {
		throw new ApiError(body.error || 'Something went wrong.', response.status, body);
	}
	return body as T;
}

/** A JSON request. The server only accepts JSON for forms, which keeps other sites from posting to it. */
export const json = (method: string, body: unknown = {}): RequestInit => ({
	method,
	headers: { 'Content-Type': 'application/json' },
	body: JSON.stringify(body)
});
