# Test Setup Instructions

## Prerequisites

1. **Node.js 18+** installed
2. **Backend server** running on `http://localhost:8000`
3. **Database** with test data

## Setup Test Environment

### 1. Install Test Dependencies

```bash
cd 1_Frontend_Football_Probability_Engine
npm install --save-dev vitest @vitest/ui @testing-library/react @testing-library/jest-dom jsdom
```

### 2. Create Vitest Config

Create `vitest.config.ts` in frontend root:

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react-swc';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

### 3. Create Test Setup File

Create `src/test/setup.ts`:

```typescript
import '@testing-library/jest-dom';
import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
});
```

## Running Tests

### Run All Tests
```bash
npm test
```

### Run with UI
```bash
npm run test:ui
```

### Run with Coverage
```bash
npm run test:coverage
```

### Run Specific Test File
```bash
npm test -- integration/backtesting-workflow.test.tsx
```

## Test Structure

Tests are located in `FrontEnd Tests/` directory:
- `integration/` - Integration tests
- `e2e/` - End-to-end tests
- `unit/` - Unit tests (to be created)

## Notes

- Tests use `fetch` API for HTTP requests
- Backend must be running for integration tests
- E2E tests may require Playwright or Cypress setup

