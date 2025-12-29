# Quick Installation Guide

## Step-by-Step Installation

Since you've already installed `pydantic-settings`, continue with:

### Option 1: Install All Dependencies (Recommended)

```bash
# Install NumPy first (avoids build issues)
pip install numpy

# Then install everything else
pip install -r requirements.txt
```

### Option 2: Use the Batch Script (Windows)

```bash
install_dependencies.bat
```

### Option 3: Install Critical Packages First

```bash
# Core FastAPI dependencies
pip install fastapi uvicorn[standard] sqlalchemy psycopg[binary]
pip install pydantic pydantic-settings python-multipart python-dotenv

# Scientific packages (install NumPy first)
pip install numpy
pip install scipy pandas scikit-learn

# Other dependencies
pip install python-Levenshtein celery redis requests httpx
pip install pytest pytest-asyncio alembic
pip install python-jose[cryptography] passlib[bcrypt] python-dateutil
```

## Verify Installation

After installation, test if everything works:

```bash
python -c "from app.config import settings; print('Config loaded successfully!')"
```

## Start the Server

Once all dependencies are installed:

```bash
npm run dev
```

Or directly:

```bash
python run.py
```

## Common Issues

### Missing Module Errors

If you get `ModuleNotFoundError`, install that specific package:

```bash
pip install <package-name>
```

### NumPy Build Errors

Install NumPy separately first:

```bash
pip install numpy
pip install -r requirements.txt
```

