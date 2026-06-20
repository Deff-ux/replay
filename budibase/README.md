# Budibase App Blueprint — Phase 2

This folder defines the MVP Budibase application structure that sits on top of the PostgreSQL schema in `db/init/001_schema.sql` plus the Phase 2 views in `db/init/002_budibase_phase2.sql`.

## Data sources

Connect Budibase to the existing `postgres` service with the same database credentials used by Docker Compose:

- Host: `postgres`
- Port: `5432`
- Database: `testdashboard`
- User: `budibase`
- Password: `${DB_PASSWORD}`

Expose these tables as editable sources:

- `test_cases`
- `suites`
- `environments`
- `test_runs` (read-only in forms except operational notes if added later)
- `artifact_files` (read-only)

Expose these views as read-only sources:

- `budibase_dashboard_product_cards`
- `budibase_dashboard_summary`
- `budibase_test_case_list`
- `budibase_run_results`
- `budibase_run_detail`

## Required screens

| Screen | Budibase source | MVP widgets and actions |
| --- | --- | --- |
| Dashboard | `budibase_dashboard_product_cards`, `budibase_dashboard_summary` | Product status cards, overall pass rate, queued/running counters. |
| Test Cases | `budibase_test_case_list` | Table with search and filters for `product`, `status`, and `tags`; row opens Test Detail. |
| Test Detail | `test_cases`, `test_runs` | Form for `steps` and `assertions`; related run history filtered by `test_case_id`. |
| Suite Builder | `suites`, `test_cases` | Suite form with ordered `test_case_ids`; product-filtered case picker. |
| Suite Run | `suites`, Runner API | Button calls `POST http://playwright-runner:8550/api/suite`; poll `GET /api/status/:runId` every 2 seconds. |
| Run Results | `budibase_run_results` | Filterable table for pass/fail/status/product and Budibase CSV export. |
| Run Detail | `budibase_run_detail` | Run metadata, JSON result, screenshot/video/log links from `artifacts`. |
| Environment | `environments` | CRUD form for staging, production, and dev base URLs. |
| Schedule | `suites` | Toggle `schedule_enabled`; edit `schedule_cron` for each suite. |

## Runner API bindings

Create Budibase REST queries against the internal Docker service URL `http://playwright-runner:8550`:

### Run single test case

- Method: `POST`
- Path: `/api/run`
- Body:

```json
{
  "testCaseId": "{{ Test Detail.Form.id }}",
  "environment": "{{ EnvironmentPicker.value }}"
}
```

### Run suite

- Method: `POST`
- Path: `/api/suite`
- Body:

```json
{
  "suiteId": "{{ Suite Builder.Form.id }}",
  "environment": "{{ EnvironmentPicker.value }}"
}
```

### Poll status

- Method: `GET`
- Path: `/api/status/{{ State.runId }}`
- Repeat: every 2 seconds while status is `queued` or `running`.

## Default schedules

The database seeds disabled schedule records for:

- Full regression: `0 23 * * 0` (Sunday 23:00).
- Smoke test: `0 6,18 * * *` (daily 06:00 and 18:00).

Enable them from the Schedule screen after assigning ordered test cases.
