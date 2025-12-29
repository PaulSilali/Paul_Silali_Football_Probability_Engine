# Frontend Environment Variables Setup

## Overview

The frontend uses environment variables for configuration. Create a `.env` file in the `1_Frontend_Football_Probability_Engine` directory.

## Required Configuration

Create a `.env` file with these settings:

```bash
# Backend API URL
# Default: http://localhost:8000/api
# For production, use your actual API domain
VITE_API_URL=http://localhost:8000/api
```

## Usage

The environment variable is accessed in `src/services/api.ts`:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
```

## Important Notes

1. **Vite Prefix**: All environment variables exposed to client code must be prefixed with `VITE_`
2. **Default Value**: If `VITE_API_URL` is not set, it defaults to `http://localhost:8000/api`
3. **Build Time**: Environment variables are embedded at build time, not runtime
4. **Security**: Never commit `.env` files to version control (already in `.gitignore`)

## Development vs Production

### Development
```bash
VITE_API_URL=http://localhost:8000/api
```

### Production
```bash
VITE_API_URL=https://api.yourdomain.com/api
```

## Quick Setup

1. Create `.env` file in the frontend root directory:
   ```bash
   cd 1_Frontend_Football_Probability_Engine
   # Create .env file with VITE_API_URL
   ```

2. Update `VITE_API_URL` to match your backend URL

3. Restart the development server:
   ```bash
   npm run dev
   ```

## Current Backend Default

The frontend defaults to `http://localhost:8000/api` which matches:
- Backend default port: `8000` (from `run.py`)
- Backend API prefix: `/api` (from `app/config.py`)

Make sure your backend is running on port 8000 or update `VITE_API_URL` accordingly.

