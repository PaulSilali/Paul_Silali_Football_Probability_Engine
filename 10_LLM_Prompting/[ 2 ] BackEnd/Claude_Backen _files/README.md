# Football Jackpot Probability Engine - Frontend

**Professional, Institutional-Grade Decision Support Interface**

A production-ready React + TypeScript frontend for the Football Jackpot Probability Engine. This interface provides probability estimation, calibration visualization, and model explainability for serious jackpot betting analysis.

---

## 🎯 Product Philosophy

This is **NOT**:
- ❌ A betting tipster
- ❌ A prediction gimmick
- ❌ A neural network demo
- ❌ A gambling entertainment app

This **IS**:
- ✅ A probability estimation dashboard
- ✅ A calibration and validation tool
- ✅ A multi-perspective decision support system
- ✅ An institutional-grade analytical interface

**Tone**: Professional, analytical, calm, institutional

---

## 📋 Features

### Core Sections

1. **Jackpot Input**
   - Manual fixture entry
   - Bulk CSV paste support
   - Real-time validation
   - Professional, neutral interface

2. **Probability Output**
   - Raw calibrated probabilities
   - No "highlighted winners"
   - Entropy and confidence metrics
   - Visual probability distributions

3. **Probability Sets Comparison**
   - 7 distinct probability perspectives (A-G)
   - Side-by-side comparison
   - Methodology explanations
   - Divergence analysis

4. **Calibration & Validation**
   - Reliability curves
   - Brier score trends
   - Expected vs observed analysis
   - Historical performance metrics

5. **Model Explainability**
   - Feature contribution analysis
   - Model vs market comparison
   - SHAP-style visualizations
   - Clear causation disclaimers

6. **Model Health**
   - Real-time drift detection
   - System integrity monitoring
   - Alert management
   - Calm, diagnostic interface

7. **System Management**
   - Model version control
   - Data coverage overview
   - Background task management
   - Training triggers

---

## 🛠 Tech Stack

### Core
- **React 18** - Modern UI library
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool
- **Tailwind CSS** - Utility-first styling

### State Management
- **Zustand** - Lightweight state management (no Redux complexity)

### Data Visualization
- **Recharts** - Declarative charts for React
- **Lucide React** - Professional icon set

### API Communication
- **Fetch API** - Native HTTP client
- **Custom error handling** - Type-safe API layer

---

## 📁 Project Structure

```
jackpot-frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # Base UI components (Button, Card, Table, etc.)
│   │   └── sections/        # Main application sections
│   │       ├── JackpotInput.tsx
│   │       ├── ProbabilityOutput.tsx
│   │       ├── ProbabilitySetsComparison.tsx
│   │       ├── CalibrationDashboard.tsx
│   │       ├── ModelExplainability.tsx
│   │       ├── ModelHealth.tsx
│   │       └── SystemManagement.tsx
│   ├── store/
│   │   └── index.ts         # Zustand state management
│   ├── api/
│   │   └── index.ts         # Backend API communication
│   ├── types/
│   │   └── index.ts         # TypeScript type definitions
│   ├── utils/
│   │   └── index.ts         # Utility functions
│   ├── App.tsx              # Main application component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles
├── public/
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── vite.config.ts
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The application will be available at `http://localhost:3000`

---

## 🎨 Design System

### Color Palette (Professional, Muted)

```css
/* Primary: Slate (neutral, institutional) */
slate-50  to slate-900

/* Accents: */
blue-500  - Primary actions
emerald-500 - Success states
amber-500   - Warnings
red-500     - Errors
```

**NO casino colors, NO green/red win highlighting, NO gamification**

### Typography

- **Sans:** Inter (clean, professional)
- **Mono:** JetBrains Mono (for numerical data)

### Components

All components follow strict design rules:
- Muted, professional colors
- No emojis (except in specific guidance contexts)
- No gambling language ("lock", "sure", "best pick")
- Neutral validation messages
- Calm, diagnostic tone

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### API Integration

The frontend expects a backend API with the following endpoints:

- `POST /api/v1/predictions` - Generate predictions
- `GET /api/v1/predictions/:id` - Retrieve prediction
- `GET /api/v1/model/status` - Get model version
- `GET /api/v1/health/model` - Get model health
- `GET /api/v1/validation/metrics` - Get validation metrics
- `POST /api/v1/data/refresh` - Trigger data refresh
- `POST /api/v1/model/train` - Trigger model training
- `GET /api/v1/tasks/:taskId` - Check task status

---

## 📊 Probability Sets

The application supports 7 distinct probability sets:

| Set | Name | Risk Profile | Description |
|-----|------|--------------|-------------|
| **A** | Pure Model | Aggressive | Statistical model only, no market influence |
| **B** | Balanced | Balanced | 60% model + 40% market (default) |
| **C** | Market-Dominant | Conservative | 80% market + 20% model |
| **D** | Draw-Boosted | Balanced | Draw probability increased 15% |
| **E** | Entropy-Penalized | Aggressive | Sharper, more decisive probabilities |
| **F** | Kelly-Weighted | Balanced | Optimized for bankroll growth |
| **G** | Ensemble | Conservative | Performance-weighted average of A, B, C |

Users can select multiple sets for side-by-side comparison.

---

## 🎯 Key UX Principles

### Language Rules

**Never use:**
- ❌ "Best pick"
- ❌ "Strong signal"
- ❌ "High confidence" (without calibration context)
- ❌ "Lock" / "Sure thing" / "Safe bet"

**Always use:**
- ✅ "Higher probability under this model"
- ✅ "Relative increase vs baseline"
- ✅ "Model-implied likelihood"
- ✅ "Estimated probability: X%"

### Error Handling

All errors are handled gracefully:
- Network failures → Retry with exponential backoff
- API errors → Clear, actionable messages
- Missing data → Fallback UI with explanation

### Loading States

- **Global loading**: Overlay with spinner
- **Section loading**: In-place spinner
- **Background tasks**: Progress bars with percentages

---

## 🧪 Testing Considerations

### Manual Testing Checklist

- [ ] Fixture input validation (team names, odds ranges)
- [ ] Bulk paste with various formats (CSV, TSV, spaces)
- [ ] Probability sum validation (should equal 100%)
- [ ] Probability set toggling
- [ ] Model-market divergence warnings
- [ ] Calibration curve rendering
- [ ] Export functionality (CSV, PDF)
- [ ] Responsive design (desktop-first, but mobile-friendly)

### Future Automated Testing

- Unit tests for utilities (probability calculations)
- Integration tests for API calls
- E2E tests for critical user flows

---

## 📦 Build & Deployment

### Production Build

```bash
npm run build
```

Output: `dist/` folder ready for static hosting

### Deployment Options

1. **Static Hosting** (Vercel, Netlify, Cloudflare Pages)
   - Zero configuration
   - Automatic HTTPS
   - CDN distribution

2. **Docker**
   ```dockerfile
   FROM nginx:alpine
   COPY dist/ /usr/share/nginx/html
   EXPOSE 80
   ```

3. **AWS S3 + CloudFront**
   - Scalable
   - Low cost
   - Global CDN

---

## 🔒 Security Considerations

### Frontend Security

- **No sensitive data in localStorage**: All authentication should be handled via HTTP-only cookies
- **CSP headers**: Content Security Policy to prevent XSS
- **Input sanitization**: All user inputs validated before API calls
- **HTTPS-only**: Enforce in production

### API Communication

- **CORS**: Configure backend to allow only production domain
- **Rate limiting**: Handle 429 responses gracefully
- **Authentication**: Support for API keys or JWT tokens

---

## 📝 API Response Examples

### Prediction Response

```json
{
  "predictionId": "550e8400-e29b-41d4-a716-446655440000",
  "modelVersion": "v2.3.1",
  "createdAt": "2025-12-28T14:30:00Z",
  "fixtures": [
    {
      "id": "fixture-1",
      "homeTeam": "Arsenal",
      "awayTeam": "Chelsea",
      "odds": {"home": 2.10, "draw": 3.40, "away": 3.20}
    }
  ],
  "probabilitySets": {
    "A_pure_model": [
      {"home": 0.48, "draw": 0.27, "away": 0.25, "entropy": 1.08}
    ],
    "B_balanced": [
      {"home": 0.52, "draw": 0.26, "away": 0.22, "entropy": 1.05}
    ]
  },
  "confidenceFlags": {
    "0": "high"
  }
}
```

---

## 🚨 Critical Reminders

1. **No Neural Network Language**: This is a statistical modeling system, not deep learning
2. **Honest Uncertainty**: Always acknowledge probability != certainty
3. **Calibration First**: Prioritize probability calibration over accuracy claims
4. **User Education**: Help users understand what probabilities mean
5. **Responsible Gambling**: Include disclaimers, avoid addiction triggers

---

## 📚 Resources

- **Main Architecture Doc**: See `jackpot_system_architecture.md`
- **API Documentation**: Backend README
- **Design System**: Tailwind documentation
- **Recharts Docs**: https://recharts.org

---

## 🤝 Contributing Guidelines

### Code Style

- Use TypeScript strictly (no `any` types unless absolutely necessary)
- Follow existing component patterns
- Keep components under 300 lines
- Extract reusable logic to utilities
- Document complex calculations

### Pull Request Process

1. Test locally with backend
2. Ensure no console errors
3. Check mobile responsiveness
4. Update types if API contract changes
5. Add comments for non-obvious logic

---

## 📄 License

Proprietary - Internal Use Only

---

## 👥 Support

For technical issues:
- Backend API: Contact backend team
- Frontend bugs: Create issue in repository
- Design questions: Refer to master prompt document

---

**Remember**: This is a professional probability estimation tool, not a gambling entertainment app. Every design decision should reflect statistical rigor, user education, and responsible use.
