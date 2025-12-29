# Install psycopg (PostgreSQL Driver)

## Issue
```
ModuleNotFoundError: No module named 'psycopg'
```

## Solution

Install psycopg with binary support:

```bash
pip install psycopg[binary]
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Note

The `psycopg[binary]` package includes pre-compiled binaries, so you don't need to build from source. This is the easiest way to install on Windows.

## After Installation

Once installed, try running the server again:

```bash
npm run dev
```

The server should start successfully on http://localhost:8000

