# API Design

Product endpoints will use `/api/v1`. `/health` stays outside the versioned API for infrastructure liveness. Planned groups are `/auth`, `/monitors`, `/incidents`, `/notifications`, `/reports`, `/maintenance-windows`, `/team` or `/members`, and `/ai`. Planned means not implemented yet.

Use JSON with `snake_case` names. Use ISO-8601 UTC timestamps. Use standard status codes: 200/201 for success, 204 for no content, 400 for invalid requests, 401 for unauthenticated, 403 for forbidden, 404 for missing resources, 409 for conflicts, 422 for validation errors, and 500 for unexpected errors.

Errors use this shape:

```json
{"error":{"code":"VALIDATION_ERROR","message":"Request data is invalid.","details":{}}}
```

Do not return internal stack traces. Log request and correlation IDs internally when available. When authentication is added, use a documented secure convention and enforce authorization on the backend. Pagination will use `limit` and `cursor`; filtering and sorting use explicit query parameters. Use idempotency keys for future create operations that may be safely retried, such as notification dispatch. FastAPI serves OpenAPI and Swagger at `/openapi.json` and `/docs`.

Each endpoint belongs to one feature module. A breaking change needs a new API version or an approved migration plan.
