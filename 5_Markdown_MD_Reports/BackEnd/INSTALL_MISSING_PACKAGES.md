# Install Missing Packages

## Current Issue

The server needs `python-multipart` for handling form data (file uploads).

## Quick Fix

Install the missing package:

```bash
pip install python-multipart
```

## Install All Remaining Dependencies

To ensure everything is installed, run:

```bash
pip install -r requirements.txt
```

This will install all packages including:
- python-multipart (for form data/file uploads)
- All other dependencies from requirements.txt

## After Installation

Once installed, restart the server:

```bash
npm run dev
```

The server should start successfully on http://localhost:8000

## Note About .env Warnings

The `.env` file parsing warnings (lines 76-97) are non-critical. They won't prevent the server from running, but you can fix them by ensuring:
- Comment lines start with `#` at the beginning (no leading spaces)
- No trailing spaces on lines
- Proper formatting

