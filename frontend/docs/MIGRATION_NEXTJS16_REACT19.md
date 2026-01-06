# Migration Guide: Next.js 14 → 16 + React 18 → 19

## Overview

This document outlines the required changes to upgrade the Portfolio Management System frontend from:
- **Next.js 14.2.35** → **Next.js 16.x**
- **React 18.3.0** → **React 19.x**

### Estimated Effort: 8-14 hours

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Package Updates](#package-updates)
3. [Breaking Changes - High Priority](#breaking-changes---high-priority)
4. [Breaking Changes - Medium Priority](#breaking-changes---medium-priority)
5. [TypeScript Changes](#typescript-changes)
6. [Library Compatibility](#library-compatibility)
7. [Testing Checklist](#testing-checklist)
8. [Rollback Plan](#rollback-plan)

---

## Prerequisites

Before starting the migration:

```bash
# Create a backup branch
git checkout -b backup/pre-nextjs16-migration
git push origin backup/pre-nextjs16-migration

# Return to main branch
git checkout main
git checkout -b feature/nextjs16-react19-migration
```

---

## Package Updates

### Step 1: Update Core Dependencies

```bash
cd frontend

# Update Next.js and React
npm install next@16.0.10 react@19.2.3 react-dom@19.2.3

# Update TypeScript types
npm install -D @types/react@19 @types/react-dom@19

# Update ESLint config (required for Next.js 16)
npm install -D eslint-config-next@16
```

### Step 2: Update package.json Scripts

**File:** `frontend/package.json`

```diff
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
-   "lint": "next lint",
+   "lint": "eslint . --ext .js,.jsx,.ts,.tsx",
    "type-check": "tsc --noEmit"
  },
```

> **Note:** Next.js 16 removes the `next lint` command. Use ESLint directly.

---

## Breaking Changes - High Priority

### 1. Async Request APIs (Route Handlers)

**Impact:** 🔴 HIGH - Your API proxy route needs changes

**Affected File:** `frontend/src/app/api/v1/[[...path]]/route.ts`

**Current Code (Already Compatible ✅):**
Your route handlers already use the async `params` pattern:
```typescript
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}
```

**Status:** ✅ No changes needed - code is already Next.js 15/16 compatible!

---

### 2. Caching Behavior Changes (Next.js 15+)

**Impact:** 🔴 HIGH - `fetch()` is no longer cached by default

**What Changed:**
- Next.js 14: `fetch()` cached by default
- Next.js 15+: `fetch()` NOT cached by default

**Files to Review:**
- `frontend/src/lib/api.ts` - Uses axios (not affected by fetch caching)
- Any Server Components using `fetch()` directly

**Action Required:**
If you add Server Components that use `fetch()`, explicitly set caching:

```typescript
// For cached requests
const data = await fetch(url, { cache: 'force-cache' });

// For dynamic requests (current default)
const data = await fetch(url, { cache: 'no-store' });
```

---

### 3. ESLint Flat Config (Next.js 16)

**Impact:** 🟡 MEDIUM - Config file format change

**Create new ESLint config:**

**File:** `frontend/eslint.config.mjs` (new file)

```javascript
import { dirname } from 'path';
import { fileURLToPath } from 'url';
import { FlatCompat } from '@eslint/eslintrc';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends('next/core-web-vitals', 'next/typescript'),
];

export default eslintConfig;
```

**Remove old config:** Delete `.eslintrc.json` if it exists.

---

### 4. Turbopack Configuration (Next.js 16)

**Impact:** 🟡 MEDIUM - Turbopack is now default

**File:** `frontend/next.config.js`

```diff
  /** @type {import('next').NextConfig} */
  const nextConfig = {
    output: 'standalone',
    reactStrictMode: true,
+   // Opt out of Turbopack if needed (not recommended)
+   // turbopack: false,
  };

  module.exports = nextConfig;
```

**Note:** Turbopack is now the default bundler. Your current simple config should work fine.

---

## Breaking Changes - Medium Priority

### 5. React 19: `forwardRef` No Longer Required

**Impact:** 🟢 LOW - Optional refactoring for cleaner code

**What Changed:**
React 19 passes `ref` as a regular prop. `forwardRef` still works but is no longer necessary.

**Affected Files (64 instances across 18 files):**
- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/ui/input.tsx`
- `frontend/src/components/ui/textarea.tsx`
- `frontend/src/components/ui/card.tsx` (6 components)
- `frontend/src/components/ui/dialog.tsx` (4 components)
- `frontend/src/components/ui/alert-dialog.tsx` (6 components)
- `frontend/src/components/ui/command.tsx` (7 components)
- `frontend/src/components/ui/dropdown-menu.tsx` (8 components)
- `frontend/src/components/ui/select.tsx` (7 components)
- `frontend/src/components/ui/table.tsx` (8 components)
- `frontend/src/components/ui/tabs.tsx` (3 components)
- `frontend/src/components/ui/toast.tsx` (6 components)
- And more...

**Example Migration (Optional):**

**Before (React 18):**
```typescript
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';
```

**After (React 19):**
```typescript
function Button({
  className,
  variant,
  size,
  asChild = false,
  ref,
  ...props
}: ButtonProps & { ref?: React.Ref<HTMLButtonElement> }) {
  const Comp = asChild ? Slot : 'button';
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      {...props}
    />
  );
}
```

**Recommendation:** Keep `forwardRef` for now - it still works and maintains backward compatibility.

---

### 6. React 19: `useRef` Requires Initial Value

**Impact:** 🟢 LOW - Your code already follows this pattern

**What Changed:**
`useRef()` without an argument is now a TypeScript error.

**Your Current Code (Already Correct ✅):**
```typescript
// frontend/src/components/charts/CandlestickChart.tsx
const containerRef = useRef<HTMLDivElement>(null);
const chartRef = useRef<IChartApi | null>(null);
```

**Status:** ✅ No changes needed - all `useRef` calls include initial values.

---

### 7. React 19: Cleanup Functions in `ref` Callbacks

**Impact:** 🟢 LOW - New feature, not breaking

**What Changed:**
Ref callbacks can now return cleanup functions:

```typescript
<div ref={(node) => {
  // Setup
  console.log('Mounted:', node);

  // Cleanup (new in React 19)
  return () => {
    console.log('Unmounted');
  };
}} />
```

**Status:** No action required - this is additive functionality.

---

### 8. React 19: Context as Provider

**Impact:** 🟢 LOW - Optional simplification

**What Changed:**
You can now use `<Context>` directly instead of `<Context.Provider>`:

```typescript
// Before
<ThemeContext.Provider value="dark">
  <App />
</ThemeContext.Provider>

// After (React 19)
<ThemeContext value="dark">
  <App />
</ThemeContext>
```

**Status:** Optional refactoring - current code will continue to work.

---

## TypeScript Changes

### Update tsconfig.json

**File:** `frontend/tsconfig.json`

No changes required. Your current configuration is compatible:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "strict": true,
    "jsx": "preserve",
    "moduleResolution": "bundler"
  }
}
```

### Type Import Updates

If you encounter type errors after upgrading `@types/react`, check for:

1. **Removed types:** `React.FC` children prop is no longer implicit
2. **Changed types:** Some event handler types may have changed

---

## Library Compatibility

### Check Third-Party Libraries

Run compatibility check after updating:

```bash
npm ls react
npm ls react-dom
```

**Libraries to verify:**
| Library | Current Version | React 19 Support |
|---------|-----------------|------------------|
| `@radix-ui/*` | Various | ✅ Supported |
| `lightweight-charts` | 5.0.7 | ✅ Supported |
| `zustand` | 5.0.5 | ✅ Supported |
| `axios` | 1.9.0 | ✅ Supported |
| `class-variance-authority` | 0.7.1 | ✅ Supported |
| `lucide-react` | 0.511.0 | ✅ Supported |
| `cmdk` | 1.1.1 | ⚠️ Check latest |

---

## Testing Checklist

### Pre-Migration Tests

```bash
# Run existing tests
npm test

# Type check
npm run type-check

# Build check
npm run build
```

### Post-Migration Tests

- [ ] Application builds without errors
- [ ] Type checking passes
- [ ] Login/Register flows work
- [ ] Dashboard loads correctly
- [ ] Charts render (CandlestickChart, EquityCurveChart)
- [ ] API proxy routes work (`/api/v1/*`)
- [ ] All UI components render correctly
- [ ] Form inputs work (Input, Textarea, Select)
- [ ] Dialogs and modals open/close
- [ ] Navigation works
- [ ] Global search functions
- [ ] Drawing tools on charts work

### Manual Testing Priority

1. **Critical Path:** Login → Dashboard → Portfolio view
2. **Charts:** Candlestick chart with indicators and drawings
3. **Forms:** Order creation, portfolio management
4. **API:** All CRUD operations through the proxy

---

## Rollback Plan

If issues arise:

```bash
# Revert to backup branch
git checkout backup/pre-nextjs16-migration

# Or revert package changes
git checkout main -- package.json package-lock.json
npm install
```

---

## Migration Steps Summary

1. ✅ Create backup branch
2. ⬜ Update packages (Next.js 16, React 19, types)
3. ⬜ Create new ESLint flat config
4. ⬜ Remove old `.eslintrc.json`
5. ⬜ Run type check and fix any errors
6. ⬜ Run build and fix any errors
7. ⬜ Test all critical paths
8. ⬜ (Optional) Refactor `forwardRef` components
9. ⬜ Update CI/CD if needed
10. ⬜ Deploy to staging for testing

---

## Additional Resources

- [Next.js 15 Upgrade Guide](https://nextjs.org/docs/app/building-your-application/upgrading/version-15)
- [Next.js 16 Release Notes](https://nextjs.org/blog/next-16)
- [React 19 Upgrade Guide](https://react.dev/blog/2024/04/25/react-19-upgrade-guide)
- [React 19 New Features](https://react.dev/blog/2024/12/05/react-19)

---

*Last Updated: January 2026*

