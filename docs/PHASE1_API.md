# Phase 1 API reference

All routes are under `/api/v1` except health checks.

| Method | Route | Auth | Purpose |
|---|---|---:|---|
| POST | `/auth/register` | No | Create user + organization + owner membership |
| POST | `/auth/login` | No | Issue access token |
| POST | `/companies/profile` | Yes | Create organization company profile |
| GET | `/companies/profile` | Yes | Read organization company profile |
| POST | `/tenders` | Yes | Add a record to the shared tender catalogue |
| GET | `/tenders` | Yes | List/filter shared tender records |
| GET | `/tenders/{id}` | Yes | Read tender |
| POST | `/tenders/{id}/requirements` | Yes | Add structured requirement |
| GET | `/tenders/{id}/requirements` | Yes | List requirements |
| GET | `/health` | No | Application health |
| GET | `/health/database` | No | Database connectivity |

Tender source values are free-form in Phase 1; planned canonical values include `cppp`, `gem`, `state_portal`, and `manual`. Requirement types: `turnover`, `experience`, `certification`, `registration`, `technical`, `emd`, `document`, `delivery`, `other`.
