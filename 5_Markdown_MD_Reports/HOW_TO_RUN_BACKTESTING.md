# How to Run Backtesting

## 📋 Overview

The Backtesting page allows you to test how well your probability predictions performed against actual match results. You can use either:
1. **Saved Results** (Recommended) - Uses real probabilities and actual results from your saved jackpots
2. **Manual/PDF/Web Import** - Import external results and generate simulated probabilities

---

## 🚀 Quick Start: Using Saved Results (Recommended)

### **Prerequisites**
- You must have saved probability results with actual outcomes entered
- Go to "Probability Output" page → Enter actual results → Save

### **Step-by-Step Instructions**

1. **Navigate to Backtesting Page**
   - Click "Backtesting" in the sidebar menu
   - The page opens with "Saved Results" tab selected by default

2. **Select a Saved Result**
   - A dropdown shows all saved results that have actual outcomes
   - Select the jackpot result you want to backtest
   - The system automatically loads:
     - Real probabilities calculated for that jackpot
     - Actual results you entered
     - Performance metrics

3. **View Results**
   - The backtest runs automatically when you select a result
   - You'll see:
     - **Performance comparison** across all 7 probability sets (A-G)
     - **Accuracy metrics** (correct predictions / total)
     - **Brier Score** (calibration quality)
     - **Log Loss** (prediction confidence)
     - **Visual charts** comparing set performance

4. **Analyze Performance**
   - Check which probability set performed best
   - Review individual match predictions vs actual outcomes
   - Identify patterns (e.g., Set B performs best overall)

---

## 📊 Alternative: Manual/PDF/Web Import

If you want to backtest external data (not from your saved results):

### **Option 1: PDF/Image Import**
1. Click "PDF/Image Import" tab
2. Upload a PDF or image with match results
3. System extracts match data automatically
4. Click "Run Backtest" to generate probabilities

### **Option 2: Manual Entry**
1. Click "Manual Entry" tab
2. Enter match results manually:
   - Home team name
   - Away team name
   - Actual result (1/X/2 or H/D/A)
   - Optional: Odds (home/draw/away)
3. Click "Run Backtest" to generate probabilities

### **Option 3: Web Import**
1. Click "Web Import" tab
2. Enter URL or scrape data from a website
3. System extracts match results
4. Click "Run Backtest" to generate probabilities

**Note**: These modes use simulated probabilities (not real model predictions), so they're useful for testing the backtesting system but not for evaluating actual model performance.

---

## 📈 Understanding Backtest Results

### **Metrics Explained**

1. **Accuracy**
   - Percentage of correct predictions
   - Formula: `(Correct Predictions / Total Matches) × 100`
   - Higher is better

2. **Brier Score**
   - Measures calibration quality
   - Range: 0.0 (perfect) to 2.0 (worst)
   - Lower is better
   - < 0.15: Well calibrated ✓
   - 0.15 - 0.2: Moderate calibration ⚠️
   - > 0.2: Poor calibration ⚠️

3. **Log Loss**
   - Measures prediction confidence
   - Lower is better
   - Typical range: 0.7 - 1.2 for football predictions

### **Probability Sets Comparison**

The backtest shows performance for all 7 sets:
- **Set A**: Pure Model (Dixon-Coles only)
- **Set B**: Market-Aware (60% model + 40% market) - **Recommended default**
- **Set C**: Market-Dominant (20% model + 80% market)
- **Set D**: Draw-Boosted (Draw +15%, renormalized)
- **Set E**: Entropy-Penalized (Sharper predictions)
- **Set F**: Kelly-Weighted (Bankroll optimized)
- **Set G**: Ensemble (Average of A, B, C)

---

## 🎯 Best Practices

1. **Use Saved Results Mode**
   - Most accurate - uses real model predictions
   - Automatically loads actual results you entered
   - No manual data entry required

2. **Backtest Multiple Jackpots**
   - Select different saved results to compare performance
   - Look for consistent patterns across jackpots
   - Identify which set performs best over time

3. **Review Individual Matches**
   - Check which matches were predicted incorrectly
   - Look for patterns (e.g., draws are hard to predict)
   - Use insights to improve future predictions

4. **Export Results**
   - After backtesting, you can export validation data
   - Go to "Jackpot Validation" page
   - Click "Export All to Training" to feed data into calibration

---

## 🔧 Troubleshooting

### **No Saved Results Available**
- **Problem**: Dropdown is empty
- **Solution**: 
  1. Go to "Probability Output" page
  2. Enter actual match results
  3. Save the results
  4. Return to Backtesting page

### **Probabilities Not Loading**
- **Problem**: "Failed to load probabilities" error
- **Solution**:
  1. Check if the jackpot ID is valid
  2. Verify the jackpot has fixtures
  3. Try refreshing the page
  4. Check backend logs for errors

### **Results Don't Match**
- **Problem**: Actual results don't align with probabilities
- **Solution**:
  1. Verify fixture IDs match between probabilities and results
  2. Check that you entered results in the correct order
  3. The system tries to match by ID first, then by index

---

## 📝 Example Workflow

1. **Week 1**: 
   - Go to "Probability Output"
   - Calculate probabilities for a jackpot
   - Save selections
   - Wait for matches to complete

2. **Week 2**:
   - Go to "Probability Output"
   - Enter actual results
   - Save updated results

3. **Week 3**:
   - Go to "Backtesting" page
   - Select the saved result from Week 1
   - Review performance metrics
   - Identify which set performed best

4. **Week 4**:
   - Use insights to improve future predictions
   - Export validation data to calibration training
   - Retrain calibration model with new data

---

## 🎓 Next Steps

After running backtests:

1. **Analyze Results**
   - Which probability set performs best?
   - Are predictions well-calibrated?
   - What patterns do you notice?

2. **Export to Training**
   - Go to "Jackpot Validation" page
   - Export validation data
   - Retrain calibration model

3. **Improve Predictions**
   - Use backtest insights to adjust strategy
   - Focus on probability sets that perform well
   - Consider model retraining if accuracy is low

---

## 🔗 Related Pages

- **Probability Output**: Calculate and save probability predictions
- **Jackpot Validation**: Compare predictions vs actuals, export to training
- **ML Training**: Retrain models with exported validation data
- **Sets Comparison**: Compare different probability sets side-by-side


