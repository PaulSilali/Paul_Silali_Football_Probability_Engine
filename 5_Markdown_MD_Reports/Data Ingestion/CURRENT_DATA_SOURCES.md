# Current Data Sources

## ✅ **Active Data Source**

### **1. Football-Data.co.uk** (Primary Source)

**Status:** ✅ **Fully Implemented and Active**

**Details:**
- **URL:** `https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv`
- **Format:** CSV files
- **Cost:** Free (no API key required)
- **Coverage:** 43 leagues across multiple countries
- **Data Available:** 20+ years of historical data for major leagues

**What Data is Provided:**
- Match results (Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR)
- Odds from multiple bookmakers (Bet365, Pinnacle, etc.)
- Historical data going back 20-30 years for major leagues

**Implementation:**
- **Backend:** `app/services/data_ingestion.py` → `download_from_football_data()`
- **API Endpoint:** `POST /api/data/refresh` and `POST /api/data/batch-download`
- **Frontend:** Data Ingestion page → "Football-Data.co.uk" tab

**Available Leagues (43 total):**

#### **England (4 leagues)**
- E0 - Premier League
- E1 - Championship
- E2 - League One
- E3 - League Two

#### **Spain (2 leagues)**
- SP1 - La Liga
- SP2 - La Liga 2

#### **Germany (2 leagues)**
- D1 - Bundesliga
- D2 - 2. Bundesliga

#### **Italy (2 leagues)**
- I1 - Serie A
- I2 - Serie B

#### **France (2 leagues)**
- F1 - Ligue 1
- F2 - Ligue 2

#### **Other European Leagues (19 leagues)**
- N1 - Eredivisie (Netherlands)
- P1 - Primeira Liga (Portugal)
- SC0-SC3 - Scottish Leagues (4 tiers)
- B1 - Pro League (Belgium)
- T1 - Super Lig (Turkey)
- G1 - Super League 1 (Greece)
- A1 - Bundesliga (Austria)
- SW1 - Super League (Switzerland)
- DK1 - Superliga (Denmark)
- SWE1 - Allsvenskan (Sweden)
- NO1 - Eliteserien (Norway)
- FIN1 - Veikkausliiga (Finland)
- PL1 - Ekstraklasa (Poland)
- RO1 - Liga 1 (Romania)
- RUS1 - Premier League (Russia)
- CZE1 - First League (Czech Republic)
- CRO1 - Prva HNL (Croatia)
- SRB1 - SuperLiga (Serbia)
- UKR1 - Premier League (Ukraine)
- IRL1 - Premier Division (Ireland)

#### **Americas (3 leagues)**
- ARG1 - Primera Division (Argentina)
- BRA1 - Serie A (Brazil)
- MEX1 - Liga MX (Mexico)

#### **Asia-Pacific (4 leagues)**
- USA1 - Major League Soccer (USA)
- CHN1 - Super League (China)
- JPN1 - J-League (Japan)
- KOR1 - K League 1 (South Korea)
- AUS1 - A-League (Australia)

**Data Fields Per Match:**
- Date
- HomeTeam, AwayTeam
- FTHG (Full Time Home Goals), FTAG (Full Time Away Goals)
- FTR (Full Time Result: H/D/A)
- B365H, B365D, B365A (Bet365 odds)
- AvgH, AvgD, AvgA (Average odds across bookmakers)
- Additional bookmaker odds (Pinnacle, etc.)

---

## 🚧 **Planned/Optional Data Source**

### **2. API-Football (RapidAPI)** (Not Implemented)

**Status:** ⚠️ **UI Placeholder Only - Not Implemented**

**Details:**
- **URL:** `https://v3.football.api-sports.io`
- **Format:** RESTful API (JSON)
- **Cost:** ~$30-60/month (depending on call volume)
- **Coverage:** 900+ leagues worldwide
- **Data Available:** Real-time fixtures + 10+ years historical

**What Data Would Be Provided:**
- Real-time fixtures and results
- Pre-match odds from 50+ bookmakers
- Opening and closing odds
- Standings, statistics
- Automated ingestion possible

**Current Status:**
- **Frontend:** Tab exists in Data Ingestion page but fields are disabled
- **Backend:** No implementation exists
- **Status:** "Not Connected" - placeholder for future implementation

**Why Not Implemented:**
- Requires paid API subscription
- Current free source (Football-Data.co.uk) meets requirements
- Can be added later for production/real-time needs

---

## 📊 **Data Source Comparison**

| Feature | Football-Data.co.uk | API-Football |
|---------|---------------------|--------------|
| **Status** | ✅ Active | 🚧 Planned |
| **Cost** | Free | ~$30-60/month |
| **Format** | CSV files | REST API (JSON) |
| **Coverage** | 43 leagues | 900+ leagues |
| **Historical Data** | 20+ years | 10+ years |
| **Real-time** | ❌ No (weekly updates) | ✅ Yes |
| **API Key Required** | ❌ No | ✅ Yes |
| **Automation** | Manual CSV download | ✅ Fully automated |
| **Odds Sources** | Multiple bookmakers | 50+ bookmakers |
| **Implementation** | ✅ Complete | ❌ Not started |

---

## 🔍 **How Data Sources Are Tracked**

### **Database Table: `data_sources`**

```sql
CREATE TABLE data_sources (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR NOT NULL UNIQUE,  -- e.g., 'football-data.co.uk'
    source_type     VARCHAR,                  -- 'csv', 'api', etc.
    status          VARCHAR,                  -- 'running', 'fresh', 'stale'
    last_sync_at    TIMESTAMPTZ,
    record_count    INTEGER,
    created_at      TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ
);
```

**Current Records:**
- `name: 'football-data.co.uk'`
- `source_type: 'csv'`
- `status: 'fresh'` (after successful download)

### **Ingestion Logs: `ingestion_logs`**

Each download operation is logged:
- Links to `data_sources` via `source_id`
- Tracks: records processed, inserted, updated, skipped
- Stores batch metadata in `logs` JSONB column

---

## 📝 **Summary**

### **Currently Using:**
1. **Football-Data.co.uk** ✅
   - Primary and only active data source
   - Free, reliable, comprehensive historical data
   - 43 leagues available
   - CSV format, manual download process

### **Planned for Future:**
2. **API-Football** 🚧
   - UI placeholder exists
   - Not implemented in backend
   - Would require paid subscription
   - Useful for real-time/production needs

### **Recommendation:**
- **Current:** Football-Data.co.uk is sufficient for model training and historical analysis
- **Future:** Consider API-Football if you need:
  - Real-time fixture updates
  - Automated daily ingestion
  - More leagues (900+ vs 43)
  - Production-grade reliability

---

## 🔗 **Related Files**

- **Frontend:** `1_Frontend_Football_Probability_Engine/src/pages/DataIngestion.tsx`
- **Backend Service:** `2_Backend_Football_Probability_Engine/app/services/data_ingestion.py`
- **API Endpoints:** `2_Backend_Football_Probability_Engine/app/api/data.py`
- **League List:** `1_Frontend_Football_Probability_Engine/src/data/allLeagues.ts`

