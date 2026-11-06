// Typed API client. Types come from src/api/schema.d.ts, which `npm run generate:api`
// generates from the backend's OpenAPI document. Do not edit schema.d.ts by hand.
import createClient from 'openapi-fetch'

import type { components, paths } from './schema'

export type Schemas = components['schemas']

export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? '',
  // Look up fetch on each call so tests can replace it.
  fetch: (request) => globalThis.fetch(request),
})
