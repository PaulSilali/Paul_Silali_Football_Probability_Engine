# Page Redesign Guide - Modern Futuristic Design

## Design Principles

1. **Glass Morphism** - Frosted glass effect with backdrop blur
2. **Gradient Accents** - Subtle gradients for primary elements
3. **Smooth Animations** - Fade-in, slide, and hover effects
4. **Real Data Only** - All cards must fetch from database
5. **Responsive Layout** - Mobile-first, works on all screen sizes
6. **Dark Mode Optimized** - Beautiful in both light and dark themes

## Design System

### Colors
- Primary: `hsl(var(--primary))` - Main brand color
- Accent: `hsl(var(--accent))` - Secondary highlights
- Muted: `hsl(var(--muted))` - Backgrounds and subtle elements
- Status Colors:
  - Stable: Green tones
  - Watch: Yellow/Orange tones
  - Degraded: Red tones

### Typography
- Headings: Bold, gradient text for main titles
- Body: Regular weight, readable sizes
- Code/Data: Monospace for numbers and IDs

### Cards
- Glass effect: `glass-card` class
- Hover: Border glow, slight elevation
- Shadows: Subtle, colored shadows
- Padding: Consistent spacing

### Animations
- Fade-in: `animate-fade-in`
- Slide-up: `animate-fade-in-up`
- Stagger: Delay based on index
- Hover: Smooth transitions

## Implementation Checklist

For each page, ensure:

- [ ] Remove all mock/hardcoded data
- [ ] Add API calls to fetch real data
- [ ] Add loading states
- [ ] Add error handling
- [ ] Apply glass morphism design
- [ ] Add smooth animations
- [ ] Ensure responsive layout
- [ ] Test with real database data

## Pages Status

### ✅ Completed
1. Dashboard - Connected to database, modern design

### 🔄 In Progress
2. ModelHealth - Needs real health monitoring endpoint

### ⏳ Pending
3-17. All other pages - Need redesign and database connection verification

## Common Patterns

### Data Fetching Pattern
```tsx
const [data, setData] = useState(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await apiClient.getData();
      setData(response.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  fetchData();
}, []);
```

### Card Pattern
```tsx
<Card className="glass-card group hover:border-primary/30 transition-all">
  <CardHeader>
    <CardTitle className="flex items-center gap-2">
      <Icon className="h-5 w-5 text-primary" />
      Title
    </CardTitle>
  </CardHeader>
  <CardContent>
    {/* Real data from database */}
  </CardContent>
</Card>
```

---

## Next Steps

1. Update ModelHealth page with real data
2. Verify all other pages use real data
3. Apply consistent design across all pages
4. Test all pages with real database

