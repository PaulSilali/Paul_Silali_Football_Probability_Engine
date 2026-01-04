# OpenFootball World Repository Structure Analysis

## Deep Scan Results

Based on analysis of the `world-master` folder, here's the complete structure and file naming conventions:

## Repository Structure

```
world-master/
├── north-america/
│   ├── major-league-soccer/     # USA1 (MLS)
│   ├── mexico/                  # MEX1 (Liga MX)
│   └── champions-league/
├── asia/
│   ├── china/                   # CHN1 (Super League)
│   ├── japan/                   # JPN1 (J1 League)
│   └── kazakhstan/
├── pacific/
│   └── australia/                # AUS1 (A-League)
├── africa/
│   ├── egypt/
│   ├── morocco/
│   ├── algeria/
│   ├── nigeria/
│   └── south-africa/
├── middle-east/
│   ├── israel/
│   └── saudi-arabia/
└── central-america/
    └── costa-rica/
```

## File Naming Patterns

### 1. Single Year Format (Calendar Year Leagues)

**Pattern**: `YYYY_LEAGUECODE.txt`

**Examples:**
- `2023_mls.txt` (USA1 - Major League Soccer)
- `2023_jp1.txt` (JPN1 - J1 League)
- `2023_cn1.txt` (CHN1 - Super League)

**Leagues using this format:**
- ✅ **USA1** (MLS): `north-america/major-league-soccer/2023_mls.txt`
- ✅ **JPN1** (J1 League): `asia/japan/2023_jp1.txt`
- ✅ **CHN1** (Super League): `asia/china/2023_cn1.txt`

### 2. Season Format (Cross-Year Leagues)

**Pattern**: `YYYY-YY_LEAGUECODE.txt`

**Examples:**
- `2023-24_mx1.txt` (MEX1 - Liga MX)
- `2023-24_au1.txt` (AUS1 - A-League)

**Leagues using this format:**
- ✅ **MEX1** (Liga MX): `north-america/mexico/2023-24_mx1.txt`
- ✅ **AUS1** (A-League): `pacific/australia/2023-24_au1.txt`

## Complete URL Patterns

### USA1 (MLS)
```
https://raw.githubusercontent.com/openfootball/world/master/north-america/major-league-soccer/2023_mls.txt
https://raw.githubusercontent.com/openfootball/world/master/north-america/major-league-soccer/2024_mls.txt
```

### MEX1 (Liga MX)
```
https://raw.githubusercontent.com/openfootball/world/master/north-america/mexico/2023-24_mx1.txt
https://raw.githubusercontent.com/openfootball/world/master/north-america/mexico/2024-25_mx1.txt
```

### JPN1 (J1 League)
```
https://raw.githubusercontent.com/openfootball/world/master/asia/japan/2023_jp1.txt
https://raw.githubusercontent.com/openfootball/world/master/asia/japan/2024_jp1.txt
```

### CHN1 (Super League)
```
https://raw.githubusercontent.com/openfootball/world/master/asia/china/2023_cn1.txt
https://raw.githubusercontent.com/openfootball/world/master/asia/china/2024_cn1.txt
```

### AUS1 (A-League)
```
https://raw.githubusercontent.com/openfootball/world/master/pacific/australia/2023-24_au1.txt
https://raw.githubusercontent.com/openfootball/world/master/pacific/australia/2024-25_au1.txt
```

## Football.TXT Format

### Header Structure
```
= Major League Soccer 2023

# Date       Sat Feb/25 - Sat Dec/9 2023 (287d)
# Teams      29
# Matches    521
# Stages     Regular Season (493)  Playoffs (28)
```

### Matchday Structure
```
» Matchday 1
  Sat Feb/25 2023
    16.55  Nashville SC            v New York City FC         2-0 (1-0)
    19.30  Atlanta United FC       v San Jose Earthquakes     2-1 (0-1)
          Charlotte FC            v New England Revolution   0-1 (0-0)
```

### Date Format
- **Pattern**: `Day Mon/Day Year`
- **Examples**: 
  - `Sat Feb/25 2023`
  - `Fri Oct/20 2023`
  - `Sun Mar/12 2023`

### Match Format
- **With time**: `HH.MM  Home Team v Away Team FT (HT)`
  - Example: `19.45  Adelaide United v Central Coast Mariners 3-0 (1-0)`
- **Without time**: `Home Team v Away Team FT (HT)`
  - Example: `Charlotte FC v New England Revolution 0-1 (0-0)`

### Key Observations
1. **Date parsing**: Use pattern `(\w+)\s+(\w+)/(\d+)\s+(\d{4})` for "Sat Feb/25 2023"
2. **Team separator**: Always uses ` v ` (space-v-space)
3. **Score format**: `FT-HT` where HT is optional in parentheses
4. **Time format**: `HH.MM` (24-hour, dot separator)
5. **Indentation**: Matches without times are indented (leading spaces)

## Updated Mapping

Based on actual structure:

| League Code | Repository | Path | File Pattern | Season Format |
|-------------|------------|------|--------------|---------------|
| **USA1** | `world` | `north-america/major-league-soccer` | `{YYYY}_mls.txt` | `YYYY` |
| **MEX1** | `world` | `north-america/mexico` | `{YYYY-YY}_mx1.txt` | `YYYY-YY` |
| **JPN1** | `world` | `asia/japan` | `{YYYY}_jp1.txt` | `YYYY` |
| **CHN1** | `world` | `asia/china` | `{YYYY}_cn1.txt` | `YYYY` |
| **AUS1** | `world` | `pacific/australia` | `{YYYY-YY}_au1.txt` | `YYYY-YY` |

## Parser Updates Required

1. ✅ **Date parsing**: Handle `Sat Feb/25 2023` format (not `Sat Aug 23, 2024`)
2. ✅ **Match parsing**: Handle `Team A v Team B score` format with optional time
3. ✅ **File naming**: Use correct patterns based on league (YYYY vs YYYY-YY)
4. ✅ **Path structure**: Use actual folder paths (e.g., `north-america/mexico` not `mexico`)

## Implementation Status

✅ **Updated**:
- File naming patterns match actual structure
- Date parsing handles `Mon/Day Year` format
- Match parsing handles `Team A v Team B score` format
- Paths use actual folder structure

## Testing Recommendations

1. Test with actual URLs:
   - `https://raw.githubusercontent.com/openfootball/world/master/north-america/major-league-soccer/2023_mls.txt`
   - `https://raw.githubusercontent.com/openfootball/world/master/north-america/mexico/2023-24_mx1.txt`
   - `https://raw.githubusercontent.com/openfootball/world/master/asia/japan/2023_jp1.txt`

2. Verify date parsing for various formats
3. Verify match parsing with and without times
4. Test season code conversion (2324 → 2023-24 for MEX1, 2023 for USA1)

