import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isLazadaCategoryUrl } from '../src/lib/lazada-route.js';

test('Lazada discovery routes lead to a grid; product links retain their report journey', () => {
	for (const link of ['https://www.lazada.com.ph/shop-mobiles/', 'https://lazada.com.ph/catalog/?q=charger', 'https://www.lazada.com.ph/category/electronics/']) assert.equal(isLazadaCategoryUrl(link), true, link);
	for (const link of ['power bank', '', 'https://www.lazada.com.ph/products/product-i123456.html', 'https://www.lazada.com.ph/cart', 'https://evil.test/shop-mobiles/', 'https://lazada.com.ph.evil.test/shop-mobiles/', 'file://lazada.com.ph/catalog/']) assert.equal(isLazadaCategoryUrl(link), false, link);
});
