# Probability Output Page Enhancements

## Summary

This document describes the enhancements made to the Probability Output page, including save functionality, score tracking, Kenyan jackpot context, and backtesting capabilities.

## Features Implemented

### 1. Save Functionality ✅
- **Similar to JackpotInput**: Users can now save their probability output selections with a name and description
- **Save Dialog**: Modal dialog for entering save details
- **Saved Results List**: Display of previously saved results for the current jackpot
- **Backend API**: New endpoints for saving/loading probability results

### 2. Table Column Validation ✅
All table columns are working correctly:
- **Home %**: Displays home win probability, clickable to select
- **Draw %**: Displays draw probability, clickable to select
- **Away %**: Displays away win probability, clickable to select
- **H (Entropy)**: Shows prediction entropy (uncertainty), color-coded
- **Conf (Confidence)**: Icon-based confidence indicator (High/Medium/Low)
- **Pick**: Shows user's selected pick (1/X/2) or recommended pick

### 3. Score Tracking ✅
- **Per-Set Scores**: Displays score (e.g., 10/15) for each probability set (A-G)
- **Real-time Calculation**: Scores update automatically when actual results are entered
- **Visual Indicators**: 
  - Green badges for correct predictions
  - Red badges for incorrect predictions
  - Score percentage display
- **Consensus Picks**: Shows recommended picks with visual feedback based on actual results

### 4. Kenyan Jackpot Context ✅
- **Currency Support**: KSH (Kenyan Shilling) as default, with USD and GBP options
- **Jackpot Types**: 
  - **15 Games**: 15M KSH (all correct), 500K (14/15), 50K (13/15)
  - **17 Games**: 200M KSH (all correct), 5M (16/17), 500K (15/17)
- **Stake Amount Explanation**: Clear explanation of stake amounts (50-1000 KSH typical range)
- **Prize Structure Display**: Visual display of prize structure in accumulator calculator

### 5. Backend API Endpoints ✅
New endpoints added:
- `POST /probabilities/{jackpot_id}/save-result` - Save probability results
- `GET /probabilities/{jackpot_id}/saved-results` - Get all saved results for a jackpot
- `GET /probabilities/saved-results/{result_id}` - Get specific saved result
- `PUT /probabilities/saved-results/{result_id}/actual-results` - Update actual results and calculate scores

### 6. Database Schema ✅
New table: `saved_probability_results`
- Stores user selections per probability set
- Stores actual results
- Stores calculated scores per set
- Supports backtesting and performance tracking

## Files Modified

### Frontend
1. **`src/pages/ProbabilityOutput.tsx`**
   - Added save dialog and functionality
   - Added actual results input section
   - Added score tracking display
   - Added saved results list
   - Enhanced consensus picks with score indicators

2. **`src/components/AccumulatorCalculator.tsx`**
   - Added Kenyan currency support (KSH)
   - Added jackpot type selection (15/17 games)
   - Added prize structure display
   - Updated stake amount explanation

3. **`src/services/api.ts`**
   - Added API methods for saving/loading probability results

### Backend
1. **`app/db/models.py`**
   - Added `SavedProbabilityResult` model

2. **`app/api/probabilities.py`**
   - Added save/load endpoints for probability results
   - Added score calculation logic

### Database
1. **`migrations/add_saved_probability_results.sql`**
   - New table schema for saved probability results

## Usage

### Saving Results
1. Make selections in the probability table (click on Home %, Draw %, or Away %)
2. Optionally enter actual results after matches complete
3. Click "Save Results" button
4. Enter name and description
5. Click "Save"

### Viewing Scores
1. Enter actual results using the "Enter Actual Results" section
2. Scores automatically calculate for each probability set
3. View scores in the consensus picks row (e.g., "Score: 10/15")
4. View score summary in the actual results section

### Using Kenyan Context
1. In Accumulator Calculator, select currency (KSH/USD/GBP)
2. Select jackpot type (15 or 17 games)
3. Enter stake amount (default 50 KSH)
4. View prize structure information

## Backtesting

Saved results can be used for backtesting:
- Compare predictions across different probability sets
- Track performance over time
- Analyze which sets perform best for different types of matches
- Export data for further analysis

## Notes

- **Stake Amount**: In Kenyan jackpots, typical stakes range from 50 KSH to 1,000 KSH per entry
- **Prize Structure**: Varies by jackpot type (15 vs 17 games)
- **Score Calculation**: Automatically calculates when actual results are entered
- **Backtesting**: Saved results include all necessary data for performance analysis

