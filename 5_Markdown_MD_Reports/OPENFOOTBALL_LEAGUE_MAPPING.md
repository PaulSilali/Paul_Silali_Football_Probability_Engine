# OpenFootball League Code Mapping

This document provides the complete mapping of league codes to OpenFootball repository paths.

## Mapping Structure

Each league is mapped to:
- **Repository**: `world`, `europe`, or `south-america`
- **Country Folder**: Country name in the repository
- **League File Pattern**: Expected file name pattern
- **Season Format**: `YYYY-YY` (e.g., `2023-24`)

## Complete Mapping

| League Code | League Name | Repository | Country Folder | League File Pattern |
|-------------|-------------|------------|----------------|---------------------|
| **SWE1** | Sweden - Allsvenskan | `europe` | `sweden` | `1-allsvenskan` |
| **FIN1** | Finland - Veikkausliiga | `europe` | `finland` | `1-veikkausliiga` |
| **RO1** | Romania - Liga 1 | `europe` | `romania` | `1-liga` |
| **RUS1** | Russia - Premier League | `europe` | `russia` | `1-premier` |
| **IRL1** | Ireland - Premier Division | `europe` | `ireland` | `1-premier` |
| **CZE1** | Czech Republic - First League | `europe` | `czech-republic` | `1-liga` |
| **CRO1** | Croatia - Prva HNL | `europe` | `croatia` | `1-hnl` |
| **SRB1** | Serbia - SuperLiga | `europe` | `serbia` | `1-superliga` |
| **UKR1** | Ukraine - Premier League | `europe` | `ukraine` | `1-premier` |
| **ARG1** | Argentina - Primera Division | `south-america` | `argentina` | `1-primera` |
| **BRA1** | Brazil - Serie A | `south-america` | `brazil` | `1-serie-a` |
| **MEX1** | Mexico - Liga MX | `world` | `mexico` | `1-liga-mx` |
| **USA1** | USA - Major League Soccer | `world` | `usa` | `1-mls` |
| **CHN1** | China - Super League | `world` | `china` | `1-super-league` |
| **JPN1** | Japan - J1 League | `world` | `japan` | `1-j1-league` |
| **KOR1** | South Korea - K League 1 | `world` | `south-korea` | `1-k-league` |
| **AUS1** | Australia - A-League | `world` | `australia` | `1-a-league` |

## URL Pattern

The service tries multiple URL patterns for each league:

1. `{season}/{league_file}.txt` (e.g., `2023-24/1-mls.txt`)
2. `{season}/{league_file}.yml` (e.g., `2023-24/1-mls.yml`)
3. `{league_file}.txt` (e.g., `1-mls.txt`)
4. `{league_file}.yml` (e.g., `1-mls.yml`)

**Base URL**: `https://raw.githubusercontent.com/openfootball/{repository}/master/{country}/{pattern}`

## Example URLs

### USA1 (MLS) - Season 2023-24
```
https://raw.githubusercontent.com/openfootball/world/master/usa/2023-24/1-mls.txt
https://raw.githubusercontent.com/openfootball/world/master/usa/2023-24/1-mls.yml
https://raw.githubusercontent.com/openfootball/world/master/usa/1-mls.txt
```

### RUS1 (Russia Premier League) - Season 2023-24
```
https://raw.githubusercontent.com/openfootball/europe/master/russia/2023-24/1-premier.txt
https://raw.githubusercontent.com/openfootball/europe/master/russia/2023-24/1-premier.yml
https://raw.githubusercontent.com/openfootball/europe/master/russia/1-premier.txt
```

### ARG1 (Argentina Primera) - Season 2023-24
```
https://raw.githubusercontent.com/openfootball/south-america/master/argentina/2023-24/1-primera.txt
https://raw.githubusercontent.com/openfootball/south-america/master/argentina/2023-24/1-primera.yml
https://raw.githubusercontent.com/openfootball/south-america/master/argentina/1-primera.txt
```

## Testing

To test which leagues are actually available, run:

```python
from app.services.ingestion.test_openfootball_urls import test_all_leagues, print_availability_report

results = test_all_leagues("2324")  # Test season 2023-24
print_availability_report(results)
```

Or use the command line:

```bash
python -m app.services.ingestion.test_openfootball_urls
```

## Notes

- **SWE1** and **FIN1** may not be available in OpenFootball repositories
- File extensions can be either `.txt` or `.yml`
- Some leagues may have different file naming conventions
- Season format is `YYYY-YY` (e.g., `2023-24` for 2023-24 season)
- The service automatically tries multiple URL patterns until one succeeds

