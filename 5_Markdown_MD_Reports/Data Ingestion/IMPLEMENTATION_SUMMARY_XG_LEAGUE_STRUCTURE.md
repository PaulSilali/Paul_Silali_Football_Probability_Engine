# Implementation Summary: xG Data & League Structure Integration

## ✅ Completed Implementations

### 1. xG Data Integration

#### Database Schema
- **Migration Script:** `3_Database_Football_Probability_Engine/migrations/2025_01_add_xg_data.sql`
- **Tables Created:**
  - `match_xg` - For jackpot fixtures
  - `match_xg_historical` - For historical matches
- **Columns:**
  - `xg_home`, `xg_away`, `xg_total`
  - `xg_draw_index` - Pre-calculated draw adjustment factor (0.8-1.2)
  - `recorded_at` - Timestamp

#### Ingestion Service
- **File:** `2_Backend_Football_Probability_Engine/app/services/ingestion/ingest_xg_data.py`
- **Functions:**
  - `ingest_xg_for_fixture()` - Single fixture ingestion
  - `ingest_xg_for_match()` - Single match ingestion
  - `batch_ingest_xg_from_matches()` - Batch processing
  - `calculate_xg_draw_index()` - Calculate draw adjustment factor
- **CSV Export:** Saves to `data/1_data_ingestion/Draw_structural/xG_Data/`

#### Draw Features Integration
- **File:** `2_Backend_Football_Probability_Engine/app/features/draw_features.py`
- **Changes:**
  - Added `xg_factor` to `DrawComponents` dataclass
  - Updated `total()` method to include xG factor
  - Updated `to_dict()` to include xG in output
  - Added xG lookup in `compute_draw_components()` function

#### API Endpoints
- **File:** `2_Backend_Football_Probability_Engine/app/api/draw_ingestion.py`
- **Request Models Added:**
  - `IngestXGDataRequest` - Single ingestion
  - `BatchIngestXGDataRequest` - Batch ingestion
- **Endpoints to Add:**
  ```python
  POST /api/draw-ingestion/xg-data
  POST /api/draw-ingestion/xg-data/batch
  GET /api/draw-ingestion/xg-data/summary
  ```

**Note:** The endpoints code is ready but needs to be appended to `draw_ingestion.py`. See code snippet below.

---

### 2. League Structure Integration

#### Enhanced League Prior Calculation
- **File:** `2_Backend_Football_Probability_Engine/app/features/draw_features.py`
- **Changes:**
  - Enhanced `compute_draw_components()` to query `league_structure` table
  - Uses `total_teams` and `relegation_zones` to adjust league prior
  - Formula:
    - `team_factor = 1.0 + (total_teams - 20) * 0.005`
    - `relegation_factor = 1.0 + (relegation_zones / 3.0) * 0.02`
    - `structure_multiplier = team_factor * relegation_factor` (bounded 0.95-1.05)
  - Applied to base league prior before final calculation

---

### 3. Metrics Tracking

#### Draw Component Tracking
- **File:** `2_Backend_Football_Probability_Engine/app/api/probabilities.py`
- **Status:** Already implemented
- **Location:** Lines 408-414, 600-604
- **Output:** Draw structural components are stored in `draw_structural_components` and included in API response metadata

---

## 📝 Code Snippets to Add

### xG Data API Endpoints (Add to `draw_ingestion.py`)

```python
@router.post("/xg-data", response_model=ApiResponse)
async def ingest_xg_data(
    request: IngestXGDataRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Ingest xG data for a fixture or match"""
    try:
        from app.services.ingestion.ingest_xg_data import ingest_xg_for_fixture, ingest_xg_for_match
        
        if request.fixture_id:
            result = ingest_xg_for_fixture(
                db=db,
                fixture_id=request.fixture_id,
                xg_home=request.xg_home,
                xg_away=request.xg_away
            )
        elif request.match_id:
            result = ingest_xg_for_match(
                db=db,
                match_id=request.match_id,
                xg_home=request.xg_home,
                xg_away=request.xg_away
            )
        else:
            raise HTTPException(status_code=400, detail="Either fixture_id or match_id must be provided")
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message="xG data ingested successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting xG data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xg-data/batch", response_model=ApiResponse)
async def batch_ingest_xg_data(
    request: BatchIngestXGDataRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Batch ingest xG data for multiple leagues and seasons"""
    try:
        from app.services.ingestion.ingest_xg_data import batch_ingest_xg_from_matches
        from app.services.data_ingestion import get_seasons_list
        
        # Convert league codes to league IDs if needed
        league_ids = None
        if request.league_codes:
            from sqlalchemy import text
            league_ids = [
                row.id for row in db.execute(
                    text("SELECT id FROM leagues WHERE code = ANY(:codes)"),
                    {"codes": request.league_codes}
                ).fetchall()
            ]
        
        # Convert season "ALL" to None
        seasons = None if request.season == "ALL" else [request.season] if request.season else None
        
        if request.use_all_seasons and request.max_years:
            seasons = get_seasons_list(request.max_years)
        
        result = batch_ingest_xg_from_matches(
            db=db,
            league_ids=league_ids,
            seasons=seasons,
            max_years=request.max_years if not seasons else None
        )
        
        return ApiResponse(
            data=result,
            success=True,
            message=f"xG data batch ingestion complete: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch xG data ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/xg-data/summary", response_model=ApiResponse)
async def get_xg_data_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for xG data"""
    try:
        from sqlalchemy import text
        
        # Get total count from both tables
        total_fixtures = 0
        try:
            total_fixtures = db.execute(text('SELECT COUNT(*) FROM match_xg')).scalar() or 0
        except:
            pass
        
        historical_count = 0
        try:
            historical_count = db.execute(text('SELECT COUNT(*) FROM match_xg_historical')).scalar() or 0
        except:
            pass
        
        total_count = total_fixtures + historical_count
        
        # Get count by league
        fixture_league_counts = []
        try:
            fixture_league_counts = db.execute(text("""
                SELECT l.code, l.name, COUNT(DISTINCT mx.id) as count
                FROM match_xg mx
                JOIN jackpot_fixtures jf ON mx.fixture_id = jf.id
                JOIN leagues l ON jf.league_id = l.id
                WHERE jf.league_id IS NOT NULL
                GROUP BY l.code, l.name
            """)).fetchall()
        except:
            pass
        
        historical_league_counts = []
        try:
            historical_league_counts = db.execute(text("""
                SELECT l.code, l.name, COUNT(DISTINCT mxh.id) as count
                FROM match_xg_historical mxh
                JOIN matches m ON mxh.match_id = m.id
                JOIN leagues l ON m.league_id = l.id
                GROUP BY l.code, l.name
            """)).fetchall()
        except:
            pass
        
        # Combine league counts
        league_dict = {}
        for row in fixture_league_counts:
            league_dict[row.code] = {"code": row.code, "name": row.name, "count": row.count}
        
        for row in historical_league_counts:
            if row.code in league_dict:
                league_dict[row.code]["count"] += row.count
            else:
                league_dict[row.code] = {"code": row.code, "name": row.name, "count": row.count}
        
        # Get most recent update
        most_recent_fixtures = None
        try:
            most_recent_fixtures = db.execute(text("""
                SELECT MAX(recorded_at) as last_updated
                FROM match_xg
            """)).fetchone()
        except:
            pass
        
        most_recent_historical = None
        try:
            most_recent_historical = db.execute(text("""
                SELECT MAX(recorded_at) as last_updated
                FROM match_xg_historical
            """)).fetchone()
        except:
            pass
        
        last_updated = None
        if most_recent_fixtures and most_recent_fixtures.last_updated:
            last_updated = most_recent_fixtures.last_updated
        if most_recent_historical and most_recent_historical.last_updated:
            if not last_updated or most_recent_historical.last_updated > last_updated:
                last_updated = most_recent_historical.last_updated
        
        leagues_with_xg = len(league_dict)
        total_leagues = db.execute(text('SELECT COUNT(*) FROM leagues')).scalar()
        
        return ApiResponse(
            data={
                "total_records": total_count,
                "leagues_with_xg": leagues_with_xg,
                "total_leagues": total_leagues,
                "last_updated": last_updated.isoformat() if last_updated else None,
                "by_league": [
                    {
                        "code": data["code"],
                        "name": data["name"],
                        "count": data["count"]
                    }
                    for data in league_dict.values()
                ]
            },
            success=True,
            message="xG data summary retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting xG data summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 🚀 Next Steps

### 1. Add xG Endpoints to `draw_ingestion.py`
- Append the code snippets above to the end of `draw_ingestion.py`
- The request models (`IngestXGDataRequest`, `BatchIngestXGDataRequest`) are already defined

### 2. Update Frontend UI
- Add "xG Data" tab to `DrawStructuralIngestion.tsx`
- Add batch ingestion controls (similar to other tabs)
- Add summary card display
- Add API client methods in `api.ts`

### 3. Run Database Migration
```sql
-- Run the migration script
\i 3_Database_Football_Probability_Engine/migrations/2025_01_add_xg_data.sql
```

### 4. Test Integration
- Test xG data ingestion for fixtures and matches
- Test batch ingestion
- Verify xG factor is included in draw components
- Verify league structure enhances league prior calculation

---

## 📊 Summary

| Feature | Status | Files Modified |
|---------|--------|----------------|
| **xG Database Tables** | ✅ Complete | `migrations/2025_01_add_xg_data.sql` |
| **xG Ingestion Service** | ✅ Complete | `app/services/ingestion/ingest_xg_data.py` |
| **xG Draw Features** | ✅ Complete | `app/features/draw_features.py` |
| **xG API Endpoints** | ⚠️ Code Ready | `app/api/draw_ingestion.py` (needs appending) |
| **League Structure Integration** | ✅ Complete | `app/features/draw_features.py` |
| **Metrics Tracking** | ✅ Complete | `app/api/probabilities.py` |
| **Frontend UI** | ⏳ Pending | `DrawStructuralIngestion.tsx`, `api.ts` |

---

## ✅ Implementation Complete

All backend components are implemented and ready. The xG endpoints need to be appended to `draw_ingestion.py`, and the frontend UI needs to be updated to expose the xG data ingestion functionality.

