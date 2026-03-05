# Fitness Tracker API Reference

This API follows OpenAPI 3 via FastAPI.

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Auth

Use Bearer auth for protected endpoints:

`Authorization: Bearer <access_token>`

### Register

- `POST /api/auth/register`
- Body:

```json
{
  "email": "user@example.com",
  "password": "pass12345"
}
```

### Login

- `POST /api/auth/login`
- Body:

```json
{
  "email": "user@example.com",
  "password": "pass12345"
}
```

## Endpoints

### Health

- `GET /health`

### User

- `GET /api/users/me`

### Metrics (Body Assessments, US units)

- `POST /api/metrics`
- `POST /api/metrics/upload/inbody` (multipart CSV upload)
- `GET /api/metrics/me`
- `GET /api/metrics/me/{metric_id}`

Body fields:

- `weight_lb`
- `body_fat_pct`
- `lean_mass_lb`
- `fat_mass_lb`
- `muscle_mass_lb`
- `visceral_fat_score`
- `waist_in`, `hip_in`, `chest_in`, `thigh_in`, `arm_in`, `calf_in`
- `measured_at`, `source`, `notes`

### Admin Metrics (Super-admin only)

- `POST /api/metrics/admin/obfuscated` (requires `reason`)
- `POST /api/metrics/admin/raw/{target_user_id}` (requires `reason`)

### Daily Activity

- `POST /api/activity/daily` (upsert by date)
- `GET /api/activity/daily?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD`

Fields:

- `steps`
- `active_calories`
- `total_calories_burned`
- `distance_miles`
- `active_minutes`
- `avg_pace_sec_per_mile`

### Goals

- `POST /api/goals`
- `GET /api/goals`
- `PATCH /api/goals/{goal_id}`
- `DELETE /api/goals/{goal_id}`

### Integrations

- `POST /api/integrations/connect`
- `GET /api/integrations`
- `POST /api/integrations/{account_id}/sync`

## Privacy model

- Users can only access their own metrics/activity/goals/integration records.
- Super-admin routes are explicit and separated.
- Raw cross-user metric access requires reason and is audited.
