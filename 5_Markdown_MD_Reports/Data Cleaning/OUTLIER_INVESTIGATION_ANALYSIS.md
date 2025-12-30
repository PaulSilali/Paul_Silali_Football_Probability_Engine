# Outlier Investigation Analysis Report

**Date:** December 29, 2025  
**Dataset:** Cleaned Football Match Data (25,221 matches)  
**Analysis Method:** IQR, Z-score, Modified Z-score

---

## 📊 **Executive Summary**

### **Overall Data Quality Score: 67.54/100**

**Outlier Rate:** 3.25% overall

**Status:** ⚠️ **MODERATE QUALITY** - Some columns require investigation

---

## 🔍 **Key Findings**

### **1. Columns with High Outlier Rates (>5%)**

| Column | Outlier % | Total Outliers | Recommendation |
|--------|-----------|----------------|----------------|
| **AvgD** (Average Draw Odds) | **9.02%** | 2,274 | 🔴 **Investigate** |
| **FTHG** (Home Goals) | **7.18%** | 1,811 | 🔴 **Investigate** |
| **AvgA** (Average Away Odds) | **6.83%** | 1,722 | 🔴 **Investigate** |
| **prob_draw_market** | **6.09%** | 1,535 | 🔴 **Investigate** |
| **AvgH** (Average Home Odds) | **5.99%** | 1,511 | 🔴 **Investigate** |

### **2. Columns with Moderate Outlier Rates (1-5%)**

| Column | Outlier % | Total Outliers | Recommendation |
|--------|-----------|----------------|----------------|
| **prob_away_market** | **2.32%** | 585 | 🟡 **Monitor** |
| **prob_home_market** | **1.20%** | 302 | 🟡 **Monitor** |

### **3. Columns with Low Outlier Rates (<1%)**

| Column | Outlier % | Total Outliers | Status |
|--------|-----------|----------------|--------|
| **FTAG** (Away Goals) | **0.33%** | 82 | ✅ **Good** |

---

## 📈 **Detailed Analysis**

### **1. AvgD (Average Draw Odds) - 9.02% Outliers** 🔴

**Statistics:**
- Mean: 3.78
- Median: 3.52
- Range: 2.09 - 16.44
- IQR Outliers: 2,274 (9.02%)
- Upper Bound: 4.695

**Analysis:**
- **Highest outlier rate** among all columns
- Maximum value (16.44) is **4.7x the median** - extreme outlier
- Likely represents matches with very high draw probabilities (defensive matches)
- **Action Required:** Verify if these are legitimate (e.g., 0-0 draws, defensive teams)

**Recommendation:**
- Review matches with AvgD > 4.695
- Check if these correspond to actual low-scoring matches
- Consider if these should be capped or flagged for special handling

---

### **2. FTHG (Full Time Home Goals) - 7.18% Outliers** 🔴

**Statistics:**
- Mean: 1.50
- Median: 1.0
- Range: 0 - 9
- IQR Outliers: 1,811 (7.18%)
- Upper Bound: 3.5

**Analysis:**
- **Right-skewed distribution** (expected for goal counts)
- Outliers are matches with **4+ home goals** (high-scoring matches)
- Maximum: 9 goals (extreme outlier - likely data error or exceptional match)
- **Action Required:** Verify legitimacy of high-scoring matches

**Visualization Insight:**
- Distribution shows:
  - Peak at 1 goal (~8,300 matches)
  - 0 goals: ~5,900 matches
  - 2 goals: ~6,100 matches
  - Rapidly decreases beyond 2 goals
  - Matches with 4+ goals are outliers

**Recommendation:**
- **Keep outliers** - High-scoring matches are legitimate (e.g., 7-2, 5-0)
- Verify matches with 8-9 goals are correct
- Consider capping at reasonable maximum (e.g., 7 goals) if data errors found

---

### **3. AvgA (Average Away Odds) - 6.83% Outliers** 🔴

**Statistics:**
- Mean: 3.79
- Median: 3.14
- Range: 1.08 - 38.04
- IQR Outliers: 1,722 (6.83%)
- Upper Bound: 6.94

**Analysis:**
- Maximum value (38.04) is **12x the median** - extreme outlier
- Likely represents matches where away team is heavy underdog
- **Action Required:** Verify if these are legitimate odds or data errors

**Recommendation:**
- Review matches with AvgA > 6.94
- Check if these correspond to actual underdog situations
- Consider capping at reasonable maximum (e.g., 20) if data errors found

---

### **4. prob_draw_market - 6.09% Outliers** 🔴

**Statistics:**
- Mean: 0.259
- Median: 0.268
- Range: 0.058 - 0.456
- IQR Outliers: 1,535 (6.09%)
- Upper Bound: 0.344

**Analysis:**
- Outliers are matches with very high draw probabilities (>34.4%)
- Maximum: 0.456 (45.6% draw probability)
- **Action Required:** Verify if these are legitimate (defensive matches, low-scoring leagues)

**Recommendation:**
- Review matches with prob_draw_market > 0.344
- Check if these correspond to actual low-scoring matches
- Consider if these should be flagged for special handling in model

---

### **5. AvgH (Average Home Odds) - 5.99% Outliers** 🔴

**Statistics:**
- Mean: 2.57
- Median: 2.26
- Range: 1.05 - 34.14
- IQR Outliers: 1,511 (5.99%)
- Upper Bound: 4.445

**Analysis:**
- Maximum value (34.14) is **15x the median** - extreme outlier
- Likely represents matches where home team is heavy underdog
- **Action Required:** Verify if these are legitimate odds or data errors

**Recommendation:**
- Review matches with AvgH > 4.445
- Check if these correspond to actual underdog situations
- Consider capping at reasonable maximum (e.g., 15) if data errors found

---

### **6. prob_away_market - 2.32% Outliers** 🟡

**Statistics:**
- Mean: 0.314
- Median: 0.300
- Range: 0.025 - 0.877
- IQR Outliers: 585 (2.32%)
- Upper Bound: 0.634

**Analysis:**
- Maximum: 0.877 (87.7% away win probability) - extreme but possible
- Outliers are matches with very high away win probabilities
- **Action Required:** Monitor - verify outliers are legitimate

**Recommendation:**
- ✅ **Accept outliers** - High away win probabilities are legitimate (strong away teams)
- Monitor for data quality but no action required

---

### **7. prob_home_market - 1.20% Outliers** 🟡

**Statistics:**
- Mean: 0.427
- Median: 0.417
- Range: 0.028 - 0.916
- IQR Outliers: 302 (1.20%)
- Upper Bound: 0.801

**Analysis:**
- Maximum: 0.916 (91.6% home win probability) - extreme but possible
- Outliers are matches with very high home win probabilities
- **Action Required:** Monitor - verify outliers are legitimate

**Recommendation:**
- ✅ **Accept outliers** - High home win probabilities are legitimate (strong home teams)
- Monitor for data quality but no action required

---

### **8. FTAG (Full Time Away Goals) - 0.33% Outliers** ✅

**Statistics:**
- Mean: 1.24
- Median: 1.0
- Range: 0 - 9
- IQR Outliers: 82 (0.33%)
- Upper Bound: 5.0

**Analysis:**
- **Lowest outlier rate** - excellent data quality
- Outliers are matches with 6+ away goals (very rare)
- **Action Required:** None - data quality is good

**Recommendation:**
- ✅ **No action required** - Outliers are legitimate high-scoring matches

---

## 🎯 **Domain-Specific Validation**

### **Expected Patterns (All Verified ✅)**

1. **Goal Distributions:**
   - ✅ Right-skewed (most matches have 0-2 goals)
   - ✅ High-scoring matches (4+ goals) are rare but legitimate
   - ✅ Maximum 9 goals is extreme but possible (e.g., 7-2, 5-4)

2. **Odds Distributions:**
   - ✅ Home odds typically lower than away odds (home advantage)
   - ✅ Extreme odds (>20) represent heavy favorites/underdogs
   - ✅ Draw probabilities typically 20-30% range

3. **Market Probabilities:**
   - ✅ Sum of probabilities should be ~1.0 (after overround removal)
   - ✅ Extreme probabilities (>80%) represent strong favorites
   - ✅ Low probabilities (<5%) represent heavy underdogs

---

## 📋 **Recommendations Summary**

### **🔴 High Priority (Investigate)**

1. **AvgD (9.02% outliers)**
   - Review matches with AvgD > 4.695
   - Verify if these are legitimate defensive matches
   - Consider capping if data errors found

2. **FTHG (7.18% outliers)**
   - Verify matches with 8-9 goals are correct
   - Keep outliers if legitimate (high-scoring matches)
   - Consider capping at 7 goals if data errors found

3. **AvgA (6.83% outliers)**
   - Review matches with AvgA > 6.94
   - Verify if these are legitimate underdog situations
   - Consider capping at 20 if data errors found

4. **prob_draw_market (6.09% outliers)**
   - Review matches with prob_draw_market > 0.344
   - Verify if these are legitimate defensive matches
   - Flag for special handling in model if needed

5. **AvgH (5.99% outliers)**
   - Review matches with AvgH > 4.445
   - Verify if these are legitimate underdog situations
   - Consider capping at 15 if data errors found

### **🟡 Medium Priority (Monitor)**

1. **prob_away_market (2.32% outliers)**
   - Monitor for data quality
   - Accept outliers if legitimate

2. **prob_home_market (1.20% outliers)**
   - Monitor for data quality
   - Accept outliers if legitimate

### **✅ Low Priority (No Action)**

1. **FTAG (0.33% outliers)**
   - No action required
   - Data quality is excellent

---

## 🔧 **Proposed Actions**

### **Immediate Actions:**

1. **Manual Review:**
   - Sample 50-100 matches from each high-outlier column
   - Verify if outliers are legitimate or data errors
   - Document findings

2. **Data Validation:**
   - Check for data entry errors (e.g., 99 instead of 9.9)
   - Verify extreme values against source data
   - Check for missing value imputation errors

3. **Capping Strategy:**
   - Consider capping extreme values at reasonable maximums:
     - Goals: Cap at 7 (matches with 8+ goals are extremely rare)
     - Odds: Cap at 20 (odds >20 are extremely rare)
     - Probabilities: Already bounded between 0-1 ✅

### **Model Training Considerations:**

1. **Outlier Handling:**
   - **Keep outliers** if legitimate (they represent real match outcomes)
   - **Robust models** (Dixon-Coles) handle outliers well
   - **Feature engineering** can help (e.g., log transform for odds)

2. **Feature Engineering:**
   - Log transform odds columns (AvgH, AvgA, AvgD) to reduce outlier impact
   - Cap extreme values before training if needed
   - Use robust statistics (median instead of mean) where appropriate

3. **Validation:**
   - Monitor model performance on outlier cases
   - Ensure model doesn't overfit to outliers
   - Use cross-validation to test robustness

---

## 📊 **Data Quality Metrics**

| Metric | Value | Status |
|--------|-------|--------|
| **Overall Quality Score** | 67.54/100 | ⚠️ Moderate |
| **Overall Outlier Rate** | 3.25% | ⚠️ Moderate |
| **Columns Analyzed** | 12 | ✅ Complete |
| **Total Rows** | 25,221 | ✅ Good |
| **Missing Values** | <0.1% | ✅ Excellent |

---

## ✅ **Conclusion**

### **Data Quality Assessment:**

**Status:** ⚠️ **MODERATE QUALITY** - Requires investigation but usable for model training

**Key Points:**
1. ✅ **Goal columns (FTHG, FTAG)** have acceptable outlier rates
2. ⚠️ **Odds columns (AvgH, AvgA, AvgD)** have high outlier rates - investigate
3. ⚠️ **Market probability columns** have moderate-high outlier rates - monitor
4. ✅ **No domain violations** found - outliers appear legitimate

### **Recommendation:**

**Proceed with model training** after:
1. Manual review of extreme outliers (sample 50-100 matches)
2. Verification of data source accuracy
3. Consider capping extreme values if data errors found
4. Use robust modeling techniques (Dixon-Coles handles outliers well)

**Expected Impact:**
- Outliers represent **real match outcomes** (high-scoring matches, extreme odds)
- **Dixon-Coles model** is robust to outliers
- **Feature engineering** (log transform) can help reduce outlier impact
- **Model performance** should not be significantly affected

---

## 📝 **Next Steps**

1. ✅ **Outlier Investigation Complete** - Report generated
2. ⏭️ **Manual Review** - Sample extreme outliers for verification
3. ⏭️ **Data Validation** - Check source data for errors
4. ⏭️ **Model Training** - Proceed with cleaned data
5. ⏭️ **Model Validation** - Monitor performance on outlier cases

---

**Report Generated:** December 29, 2025  
**Analysis Tool:** `outlier_investigation.ipynb`  
**Data Source:** `2_Backend_Football_Probability_Engine/data/2_Cleaned_data/`

