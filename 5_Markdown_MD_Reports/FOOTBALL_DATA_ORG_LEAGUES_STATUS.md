# Football-Data.org Leagues Download Status

## Overview
There are **17 leagues** configured to use Football-Data.org API (not available on football-data.co.uk).

## League Breakdown

### Europe - Extra Leagues (9 leagues)

| League Code | League Name | Country | Status | Notes |
|------------|-------------|---------|--------|-------|
| **SWE1** | Allsvenskan | Sweden | ❌ **403 Forbidden** | Requires paid subscription (Tier 2+) |
| **FIN1** | Veikkausliiga | Finland | ❌ **403 Forbidden** | Requires paid subscription (Tier 2+) |
| **RO1** | Liga 1 | Romania | ❓ **Unknown** | Likely requires paid subscription |
| **RUS1** | Premier League | Russia | ❓ **Unknown** | Likely requires paid subscription |
| **IRL1** | Premier Division | Ireland | ❓ **Unknown** | Likely requires paid subscription |
| **CZE1** | First League | Czech Republic | ❓ **Unknown** | Likely requires paid subscription |
| **CRO1** | Prva HNL | Croatia | ❓ **Unknown** | Likely requires paid subscription |
| **SRB1** | SuperLiga | Serbia | ❓ **Unknown** | Likely requires paid subscription |
| **UKR1** | Premier League | Ukraine | ❓ **Unknown** | Likely requires paid subscription |

### Americas (4 leagues)

| League Code | League Name | Country | Status | Notes |
|------------|-------------|---------|--------|-------|
| **ARG1** | Primera Division | Argentina | ❓ **Unknown** | Requires paid subscription |
| **BRA1** | Serie A | Brazil | ❓ **Unknown** | Requires paid subscription |
| **MEX1** | Liga MX | Mexico | ❓ **Unknown** | Requires paid subscription |
| **USA1** | Major League Soccer | USA | ❓ **Unknown** | May require paid subscription |

### Asia & Oceania (4 leagues)

| League Code | League Name | Country | Status | Notes |
|------------|-------------|---------|--------|-------|
| **CHN1** | Super League | China | ❓ **Unknown** | Requires paid subscription |
| **JPN1** | J-League | Japan | ❓ **Unknown** | Requires paid subscription |
| **KOR1** | K League 1 | South Korea | ❓ **Unknown** | Requires paid subscription |
| **AUS1** | A-League | Australia | ❓ **Unknown** | Requires paid subscription |

## Summary

### Current Status (Based on Testing)
- **Tested & Failed**: 2 leagues (SWE1, FIN1) - Both return 403 Forbidden
- **Not Yet Tested**: 15 leagues

### Expected Results (Free Tier)
Based on Football-Data.org's free tier limitations:
- **Free Tier Typically Includes**: Only major European leagues (Premier League, La Liga, Serie A, Bundesliga, Ligue 1)
- **Expected Downloadable with Free Tier**: **0-2 leagues** (possibly none)
- **Require Paid Subscription**: **15-17 leagues** (likely all of them)

### Expected Results (Paid Tier)
With a paid subscription (Tier 2 or higher):
- **Expected Downloadable**: **All 17 leagues** (assuming correct competition IDs)

## Recommendations

1. **Verify Competition IDs**: Some competition IDs may be incorrect. Check at https://www.football-data.org/documentation/api

2. **Check Subscription Tier**: 
   - Free tier: Very limited access
   - Tier 2: Access to most European leagues
   - Tier 3+: Access to all competitions

3. **Test Remaining Leagues**: Test the other 15 leagues to confirm their status

4. **Alternative Data Sources**: Consider using football-data.co.uk for leagues that are available there (currently 26+ leagues available)

## Football-Data.co.uk Leagues (Available)
These leagues are successfully downloading from football-data.co.uk:
- A1, B1, D1, D2, DK1, E0, E1, E2, E3, F1, F2, G1, I1, I2, N1, NO1, P1, PL1, SC0, SC1, SC2, SC3, SP1, SP2, SW1, T1 (26+ leagues)

## Next Steps

1. **If you have a paid subscription**: Verify competition IDs and test all 17 leagues
2. **If you have free tier**: Expect 0-2 leagues to work, consider upgrading subscription
3. **For immediate data**: Use football-data.co.uk leagues (26+ available)

