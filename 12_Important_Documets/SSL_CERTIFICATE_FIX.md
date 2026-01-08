# SSL Certificate Verification Fix

## Problem

The data ingestion service was failing with SSL certificate verification errors when downloading data from `football-data.co.uk`:

```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate
```

This is a common issue on Windows when Python doesn't have access to the system's CA certificate bundle.

---

## Solution

Added a configurable SSL verification setting that allows disabling SSL verification for development/testing environments.

### **Configuration**

**File:** `2_Backend_Football_Probability_Engine/app/config.py`

Added new setting:
```python
# SSL/TLS Configuration
# Set to False to disable SSL certificate verification (for development/testing only)
# WARNING: Disabling SSL verification is insecure and should only be used in development
VERIFY_SSL: bool = True
```

### **Usage**

#### **Option 1: Disable SSL Verification (Development Only)**

Add to your `.env` file:
```env
VERIFY_SSL=False
```

**⚠️ WARNING:** This disables SSL certificate verification, which is **insecure**. Only use this in development/testing environments, never in production.

#### **Option 2: Fix SSL Certificates (Recommended for Production)**

**Windows:**
1. Download Python's certificate bundle: https://curl.se/ca/cacert.pem
2. Set environment variable:
   ```env
   SSL_CERT_FILE=C:\path\to\cacert.pem
   ```
   Or add to your `.env` file:
   ```env
   SSL_CERT_FILE=C:\path\to\cacert.pem
   ```

**Linux/Mac:**
Usually works out of the box. If not, install certificates:
```bash
# Ubuntu/Debian
sudo apt-get install ca-certificates

# macOS
# Certificates are usually already installed
```

---

## Changes Made

### **1. Configuration (`app/config.py`)**
- Added `VERIFY_SSL: bool = True` setting

### **2. Data Ingestion Service (`app/services/data_ingestion.py`)**
- Updated `download_from_football_data()` to use `verify=settings.VERIFY_SSL`
- Added SSL warning suppression when verification is disabled
- Updated alternative URL requests

### **3. Weather Ingestion (`app/services/ingestion/ingest_weather.py`)**
- Updated Open-Meteo API requests to use `verify=settings.VERIFY_SSL`
- Added SSL warning suppression

### **4. H2H Stats Ingestion (`app/services/ingestion/ingest_h2h_stats.py`)**
- Updated API-Football requests to use `verify=settings.VERIFY_SSL`
- Added SSL warning suppression

---

## Testing

After setting `VERIFY_SSL=False` in your `.env` file, the SSL errors should be resolved. You should see:

```
WARNING - SSL certificate verification is DISABLED. This is insecure and should only be used in development!
```

And data downloads should proceed without SSL errors.

---

## Security Notes

1. **Development Only:** `VERIFY_SSL=False` should **only** be used in development/testing
2. **Production:** Always use `VERIFY_SSL=True` in production and fix certificate issues properly
3. **Man-in-the-Middle:** Disabling SSL verification makes you vulnerable to MITM attacks
4. **Best Practice:** Fix certificate issues rather than disabling verification

---

## Alternative Solutions

### **1. Install Certifi Package**
```bash
pip install certifi
```

Then set in code:
```python
import certifi
import os
os.environ['SSL_CERT_FILE'] = certifi.where()
```

### **2. Use Requests with Cert Bundle**
```python
import certifi
response = requests.get(url, verify=certifi.where())
```

### **3. Update Python Certificates**
```bash
# Windows (using pip)
pip install --upgrade certifi

# Then set environment variable
set SSL_CERT_FILE=%LOCALAPPDATA%\Programs\Python\Python314\Lib\site-packages\certifi\cacert.pem
```

---

## Status

✅ **Fixed** - SSL verification is now configurable
✅ **All requests updated** - All `requests.get()` calls now respect `VERIFY_SSL` setting
✅ **Warnings added** - System warns when SSL verification is disabled

