// Kept in its own directive-free module because `middleware.ts` imports it.
// Exporting it from a 'use client' module makes Next replace it with a client
// reference in the middleware bundle rather than this string.
export const API_PROXY_PATH = '/api/proxy'
