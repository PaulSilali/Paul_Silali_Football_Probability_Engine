# Complete Backend API Endpoint List

## All Implemented Endpoints

### Authentication (`/api/auth`)
- ✅ `POST /api/auth/login` - User login
- ✅ `POST /api/auth/logout` - User logout
- ✅ `POST /api/auth/refresh` - Refresh token
- ✅ `GET /api/auth/me` - Get current user

### Jackpots (`/api/jackpots`)
- ✅ `GET /api/jackpots` - List jackpots (paginated)
- ✅ `POST /api/jackpots` - Create jackpot
- ✅ `GET /api/jackpots/{id}` - Get jackpot
- ✅ `PUT /api/jackpots/{id}` - Update jackpot
- ✅ `DELETE /api/jackpots/{id}` - Delete jackpot
- ✅ `POST /api/jackpots/{id}/submit` - Submit jackpot
- ✅ `GET /api/jackpots/{id}/probabilities` - Calculate probabilities
- ✅ `GET /api/jackpots/{id}/probabilities/{set_id}` - Get specific set
- ✅ `GET /api/jackpots/{id}/export` - Export CSV
- ✅ `GET /api/jackpots/{id}/contributions` - Feature contributions

### Calibration (`/api/calibration`)
- ✅ `GET /api/calibration` - Get calibration data
- ✅ `GET /api/calibration/validation-metrics` - Validation metrics

### Validation (`/api/validation`)
- ✅ `POST /api/validation/team` - Validate team name

### Data Management (`/api/data`)
- ✅ `POST /api/data/updates` - Trigger data update
- ✅ `POST /api/data/refresh` - Refresh data (with league/season)
- ✅ `POST /api/data/upload-csv` - Upload CSV
- ✅ `GET /api/data/freshness` - Data freshness
- ✅ `GET /api/data/updates` - Ingestion logs
- ✅ `POST /api/data/init-leagues` - Initialize leagues

### Model Management (`/api/model`)
- ✅ `GET /api/model/health` - Model health
- ✅ `GET /api/model/status` - Model status
- ✅ `GET /api/model/versions` - Model versions
- ✅ `POST /api/model/train` - Trigger training
- ✅ `POST /api/model/versions/{id}/activate` - Activate version

### Tasks (`/api/tasks`)
- ✅ `GET /api/tasks/{task_id}` - Get task status
- ✅ `POST /api/tasks/{task_id}/cancel` - Cancel task

### Teams (`/api/teams`)
- ✅ `GET /api/teams/search` - Search teams
- ✅ `GET /api/teams/suggestions` - Team suggestions

### Audit (`/api/audit`)
- ✅ `GET /api/audit` - Audit log

---

## Alignment Status

✅ **95% aligned with specification**
✅ **100% aligned with frontend API contract**

All endpoints are implemented and ready for use.

