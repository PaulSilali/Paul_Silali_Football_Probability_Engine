# Fix .env File Parsing Warnings

## Issue

You're seeing warnings like:
```
python-dotenv could not parse statement starting at line 76
python-dotenv could not parse statement starting at line 78
...
```

These warnings are **non-critical** - your server still runs, but they indicate formatting issues in your `.env` file.

## Quick Fix

### Option 1: Check Your .env File

Run the diagnostic script:
```bash
python check_env.py
```

This will show you exactly which lines have issues.

### Option 2: Common Issues and Fixes

The warnings on lines 76-97 are likely caused by:

1. **Comment lines with leading spaces**
   - ❌ Wrong: ` # This is a comment`
   - ✅ Correct: `# This is a comment`

2. **Spaces around `=`**
   - ❌ Wrong: `KEY = value`
   - ✅ Correct: `KEY=value`

3. **Blank lines with spaces**
   - ❌ Wrong: `    ` (line with only spaces)
   - ✅ Correct: `` (empty line)

4. **Trailing spaces**
   - ❌ Wrong: `KEY=value    `
   - ✅ Correct: `KEY=value`

### Option 3: Use Clean Template

If you want to start fresh, use the clean template from `check_env.py`:

```bash
python check_env.py
# Choose option 1 to see the clean template
```

Then copy it to your `.env` file and update your values.

## Note

These warnings won't prevent your server from running. They're just python-dotenv being strict about formatting. The server will use default values or values that were parsed correctly.

## Suppress Warnings (Optional)

If you want to suppress these warnings, you can set an environment variable:

```bash
# Windows PowerShell
$env:DOTENV_IGNORE_WARNINGS="true"
npm run dev

# Or add to your .env file (though this might cause a warning itself)
DOTENV_IGNORE_WARNINGS=true
```

But it's better to fix the formatting issues in your `.env` file.

