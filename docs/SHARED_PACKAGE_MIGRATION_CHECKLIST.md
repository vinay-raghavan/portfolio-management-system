# Shared Package Migration Checklist

## Overview
This checklist guides the migration of ~6000 lines of duplicate code from `backend/` and `trading-engine/` into a shared package.

**Estimated Effort:** 2-3 days  
**Risk Level:** Medium (requires careful testing)  
**Impact:** High (eliminates 85% of code duplication)

---

## Pre-Migration Setup

### ✅ Phase 0: Preparation
- [ ] Review and approve CODE_DUPLICATION_ANALYSIS.md
- [ ] Review and approve DUPLICATION_DETAILED_COMPARISON.md
- [ ] Create feature branch: `feature/shared-package-migration`
- [ ] Backup current codebase
- [ ] Ensure all tests pass in current state
  - [ ] Backend tests: `cd backend && uv run pytest`
  - [ ] Trading-engine tests: `cd trading-engine && uv run pytest`
- [ ] Document current import patterns for rollback reference

---

## Phase 1: Create Shared Package Structure

### ✅ Step 1.1: Create Directory Structure
```bash
mkdir -p shared/{providers/{broker,data},strategies/{indicators,intraday,swing},models,core,utils,tests}
```

- [ ] Create `shared/` directory
- [ ] Create `shared/__init__.py`
- [ ] Create `shared/README.md`
- [ ] Create `shared/providers/` directory structure
- [ ] Create `shared/strategies/` directory structure
- [ ] Create `shared/models/` directory
- [ ] Create `shared/core/` directory
- [ ] Create `shared/utils/` directory
- [ ] Create `shared/tests/` directory

### ✅ Step 1.2: Create Package Configuration
- [ ] Create `shared/pyproject.toml` with dependencies
- [ ] Create `shared/py.typed` for type hints
- [ ] Create `shared/.gitignore`
- [ ] Create `shared/tests/conftest.py`

### ✅ Step 1.3: Create Empty Module Files
- [ ] `shared/__init__.py`
- [ ] `shared/providers/__init__.py`
- [ ] `shared/providers/broker/__init__.py`
- [ ] `shared/providers/data/__init__.py`
- [ ] `shared/strategies/__init__.py`
- [ ] `shared/strategies/indicators/__init__.py`
- [ ] `shared/strategies/intraday/__init__.py`
- [ ] `shared/strategies/swing/__init__.py`
- [ ] `shared/models/__init__.py`
- [ ] `shared/core/__init__.py`
- [ ] `shared/utils/__init__.py`

---

## Phase 2: Migrate Provider Schemas & Symbols

### ✅ Step 2.1: Migrate Provider Schemas
- [ ] Copy `backend/app/providers/schemas.py` to `shared/providers/schemas.py`
- [ ] Merge differences from `trading-engine/engine/providers/schemas.py`
  - [ ] Add `TRIGGERED` to `OrderStatus` enum
  - [ ] Reconcile `ProductType` enum differences
  - [ ] Reconcile `Position` model differences
- [ ] Update imports in `shared/providers/schemas.py`
- [ ] Add comprehensive docstrings
- [ ] Create tests: `shared/tests/test_schemas.py`
- [ ] Run tests: `cd shared && uv run pytest tests/test_schemas.py`

### ✅ Step 2.2: Migrate Symbol Utilities
- [ ] Copy `backend/app/providers/symbols.py` to `shared/providers/symbols.py`
- [ ] Verify 100% identical with trading-engine version
- [ ] Update imports
- [ ] Create tests: `shared/tests/test_symbols.py`
- [ ] Run tests

---

## Phase 3: Migrate Broker Providers

### ✅ Step 3.1: Migrate Broker Base Class
- [ ] Copy `backend/app/providers/broker/base.py` to `shared/providers/broker/base.py`
- [ ] Update imports to use `shared.providers.schemas`
- [ ] Verify abstract methods are complete
- [ ] Create tests: `shared/tests/providers/test_broker_base.py`

### ✅ Step 3.2: Migrate Broker Factory
- [ ] Copy `backend/app/providers/broker/factory.py` to `shared/providers/broker/factory.py`
- [ ] Update imports
- [ ] Update config references (use dependency injection)
- [ ] Create tests: `shared/tests/providers/test_broker_factory.py`

### ✅ Step 3.3: Migrate Paper Broker
- [ ] Copy `backend/app/providers/broker/paper.py` to `shared/providers/broker/paper.py`
- [ ] Update imports
- [ ] Reconcile minor differences between backend/engine versions
- [ ] Create tests: `shared/tests/providers/test_paper_broker.py`
- [ ] Run all broker tests

### ✅ Step 3.4: Update Broker __init__.py
- [ ] Update `shared/providers/broker/__init__.py` with exports
- [ ] Verify all classes are exported correctly

---

## Phase 4: Migrate Data Providers

### ✅ Step 4.1: Migrate Data Provider Base Class
- [ ] Copy `backend/app/providers/data/base.py` to `shared/providers/data/base.py`
- [ ] Update imports to use `shared.providers.schemas`
- [ ] Create tests: `shared/tests/providers/test_data_base.py`

### ✅ Step 4.2: Migrate Data Provider Factory
- [ ] Copy `backend/app/providers/data/factory.py` to `shared/providers/data/factory.py`
- [ ] Include NSE provider registration from backend
- [ ] Update imports
- [ ] Update config references
- [ ] Create tests: `shared/tests/providers/test_data_factory.py`

### ✅ Step 4.3: Migrate Yahoo Data Provider
- [ ] Copy `backend/app/providers/data/yahoo.py` to `shared/providers/data/yahoo.py`
- [ ] Update imports
- [ ] Create tests: `shared/tests/providers/test_yahoo_provider.py`

### ✅ Step 4.4: Migrate NSE Data Provider
- [ ] Copy `backend/app/providers/data/nse.py` to `shared/providers/data/nse.py`
- [ ] Copy `backend/app/providers/data/rate_limiter.py` to `shared/providers/data/rate_limiter.py`
- [ ] Update imports
- [ ] Create tests: `shared/tests/providers/test_nse_provider.py`

### ✅ Step 4.5: Update Data Provider __init__.py
- [ ] Update `shared/providers/data/__init__.py` with exports

---

## Phase 5: Migrate Signal Models

### ✅ Step 5.1: Migrate Signal Models
- [ ] Copy `backend/app/modules/signals/models.py` signal classes to `shared/models/signals.py`
- [ ] Verify identical with `trading-engine/engine/models/signals.py`
- [ ] Update imports
- [ ] Create tests: `shared/tests/models/test_signals.py`

---

## Phase 6: Migrate Strategy Infrastructure

### ✅ Step 6.1: Migrate Base Strategy
- [ ] Copy `backend/app/modules/signals/strategies/base.py` to `shared/strategies/base.py`
- [ ] Update imports to use `shared.models.signals`
- [ ] Create tests: `shared/tests/strategies/test_base.py`

### ✅ Step 6.2: Migrate Strategy Registry
- [ ] Copy `backend/app/modules/signals/strategies/registry.py` to `shared/strategies/registry.py`
- [ ] Update imports
- [ ] Create tests: `shared/tests/strategies/test_registry.py`

### ✅ Step 6.3: Migrate Composite Strategy
- [ ] Copy `backend/app/modules/signals/strategies/composite.py` to `shared/strategies/composite.py`
- [ ] Update imports
- [ ] Create tests: `shared/tests/strategies/test_composite.py`

### ✅ Step 6.4: Migrate Prebuilt Strategies
- [ ] Copy `backend/app/modules/signals/strategies/prebuilt.py` to `shared/strategies/prebuilt.py`
- [ ] Update imports
- [ ] Create tests: `shared/tests/strategies/test_prebuilt.py`

---

## Phase 7: Migrate Indicator Strategies

### ✅ Step 7.1: Migrate RSI Strategy
- [ ] Copy to `shared/strategies/indicators/rsi.py`
- [ ] Update imports
- [ ] Create tests: `shared/tests/strategies/indicators/test_rsi.py`

### ✅ Step 7.2: Migrate MACD Strategy
- [ ] Copy to `shared/strategies/indicators/macd.py`
- [ ] Update imports
- [ ] Create tests: `shared/tests/strategies/indicators/test_macd.py`

### ✅ Step 7.3: Migrate Moving Average Strategy
- [ ] Copy to `shared/strategies/indicators/moving_average.py`
- [ ] Update imports
- [ ] Create tests: `shared/tests/strategies/indicators/test_moving_average.py`

### ✅ Step 7.4: Migrate Bollinger Bands Strategy
- [ ] Copy to `shared/strategies/indicators/bollinger.py`
- [ ] Update imports
- [ ] Create tests: `shared/tests/strategies/indicators/test_bollinger.py`

---

## Phase 8: Migrate Intraday Strategies

### ✅ Step 8.1: Migrate VWAP Strategies
- [ ] Copy to `shared/strategies/intraday/vwap.py`
- [ ] Copy to `shared/strategies/intraday/vwap_momentum.py`
- [ ] Update imports
- [ ] Create tests

### ✅ Step 8.2: Migrate ORB Strategy
- [ ] Copy to `shared/strategies/intraday/orb.py`
- [ ] Update imports
- [ ] Create tests

### ✅ Step 8.3: Migrate Gap and Go Strategy
- [ ] Copy to `shared/strategies/intraday/gap_go.py`
- [ ] Update imports
- [ ] Create tests

### ✅ Step 8.4: Migrate TWAP Strategy
- [ ] Copy to `shared/strategies/intraday/twap.py`
- [ ] Update imports
- [ ] Create tests

---

## Phase 9: Migrate Swing Strategies

### ✅ Step 9.1: Migrate Price Action Volume Swing
- [ ] Copy to `shared/strategies/swing/price_action_volume_swing.py`
- [ ] Update imports
- [ ] Create tests

---

## Phase 10: Update Backend to Use Shared Package

### ✅ Step 10.1: Update Backend Dependencies
- [ ] Add `shared` to `backend/pyproject.toml`
- [ ] Run `cd backend && uv sync`
- [ ] Verify shared package is installed

### ✅ Step 10.2: Update Backend Imports - Providers
- [ ] Update `backend/app/modules/trading/service.py` imports
- [ ] Update `backend/app/modules/portfolio/service.py` imports
- [ ] Update `backend/app/modules/signals/service.py` imports
- [ ] Update `backend/app/modules/backtest/service.py` imports
- [ ] Update `backend/app/modules/algo/service.py` imports
- [ ] Update all other files importing from `app.providers.*`
- [ ] Search and replace: `from app.providers` → `from shared.providers`

### ✅ Step 10.3: Update Backend Imports - Strategies
- [ ] Update `backend/app/modules/signals/service.py` strategy imports
- [ ] Update `backend/app/modules/backtest/service.py` strategy imports
- [ ] Update `backend/app/modules/algo/service.py` strategy imports
- [ ] Update `backend/app/main.py` strategy registration
- [ ] Search and replace: `from app.modules.signals.strategies` → `from shared.strategies`

### ✅ Step 10.4: Update Backend Imports - Models
- [ ] Update signal model imports
- [ ] Search and replace: `from app.modules.signals.models` → `from shared.models.signals`

### ✅ Step 10.5: Remove Duplicated Backend Files
- [ ] Remove `backend/app/providers/broker/` (keep __init__.py as redirect if needed)
- [ ] Remove `backend/app/providers/data/` (keep __init__.py as redirect if needed)
- [ ] Remove `backend/app/providers/schemas.py`
- [ ] Remove `backend/app/providers/symbols.py`
- [ ] Remove `backend/app/modules/signals/strategies/` (all strategy files)
- [ ] Keep `backend/app/modules/signals/models.py` but remove signal classes

### ✅ Step 10.6: Test Backend
- [ ] Run backend tests: `cd backend && uv run pytest`
- [ ] Fix any import errors
- [ ] Fix any test failures
- [ ] Run backend server: `uv run uvicorn app.main:app --reload`
- [ ] Verify API endpoints work
- [ ] Test strategy execution
- [ ] Test broker operations

---

## Phase 11: Update Trading-Engine to Use Shared Package

### ✅ Step 11.1: Update Trading-Engine Dependencies
- [ ] Add `shared` to `trading-engine/pyproject.toml`
- [ ] Run `cd trading-engine && uv sync`
- [ ] Verify shared package is installed

### ✅ Step 11.2: Update Trading-Engine Imports - Providers
- [ ] Update `trading-engine/engine/algo/executor.py` imports
- [ ] Update `trading-engine/engine/routes/execution.py` imports
- [ ] Update all other files importing from `engine.providers.*`
- [ ] Search and replace: `from engine.providers` → `from shared.providers`

### ✅ Step 11.3: Update Trading-Engine Imports - Strategies
- [ ] Update `trading-engine/engine/algo/executor.py` strategy imports
- [ ] Update `trading-engine/engine/main.py` strategy registration
- [ ] Search and replace: `from engine.strategies` → `from shared.strategies`

### ✅ Step 11.4: Update Trading-Engine Imports - Models
- [ ] Update signal model imports
- [ ] Search and replace: `from engine.models.signals` → `from shared.models.signals`

### ✅ Step 11.5: Remove Duplicated Trading-Engine Files
- [ ] Remove `trading-engine/engine/providers/broker/`
- [ ] Remove `trading-engine/engine/providers/data/`
- [ ] Remove `trading-engine/engine/providers/schemas.py`
- [ ] Remove `trading-engine/engine/providers/symbols.py`
- [ ] Remove `trading-engine/engine/strategies/` (all strategy files)
- [ ] Remove `trading-engine/engine/models/signals.py`

### ✅ Step 11.6: Test Trading-Engine
- [ ] Run trading-engine tests: `cd trading-engine && uv run pytest`
- [ ] Fix any import errors
- [ ] Fix any test failures
- [ ] Run trading-engine server: `uv run uvicorn engine.main:app --port 8001 --reload`
- [ ] Verify internal endpoints work
- [ ] Test strategy execution
- [ ] Test broker operations

---

## Phase 12: Update Worker to Use Shared Package

### ✅ Step 12.1: Update Worker Dependencies
- [ ] Add `shared` to `worker/pyproject.toml`
- [ ] Run `cd worker && uv sync`

### ✅ Step 12.2: Update Worker Imports
- [ ] Update any worker tasks that import providers or strategies
- [ ] Search and replace imports as needed

### ✅ Step 12.3: Test Worker
- [ ] Run worker tests: `cd worker && uv run pytest`
- [ ] Test Celery tasks

---

## Phase 13: Integration Testing

### ✅ Step 13.1: Docker Compose Testing
- [ ] Build all containers: `docker-compose build`
- [ ] Start all services: `docker-compose up`
- [ ] Verify backend starts successfully
- [ ] Verify trading-engine starts successfully
- [ ] Verify worker starts successfully
- [ ] Check logs for import errors

### ✅ Step 13.2: End-to-End Testing
- [ ] Test creating a strategy via backend API
- [ ] Test executing a strategy via trading-engine
- [ ] Test backtest functionality
- [ ] Test signal generation
- [ ] Test broker operations (paper trading)
- [ ] Test data provider operations

### ✅ Step 13.3: Performance Testing
- [ ] Verify no performance degradation
- [ ] Check import times
- [ ] Check strategy execution times

---

## Phase 14: Documentation & Cleanup

### ✅ Step 14.1: Update Documentation
- [ ] Update README.md with shared package info
- [ ] Update ARCHITECTURE_v2.md
- [ ] Create `shared/README.md` with usage guide
- [ ] Document import patterns
- [ ] Update developer onboarding docs

### ✅ Step 14.2: Code Cleanup
- [ ] Remove any remaining duplicate files
- [ ] Clean up unused imports
- [ ] Run linters: `ruff check .`
- [ ] Run formatters: `ruff format .`
- [ ] Update type hints

### ✅ Step 14.3: Final Verification
- [ ] All backend tests pass
- [ ] All trading-engine tests pass
- [ ] All worker tests pass
- [ ] All shared package tests pass
- [ ] Docker compose works
- [ ] No import errors in logs
- [ ] Code coverage maintained or improved

---

## Phase 15: Deployment

### ✅ Step 15.1: Pre-Deployment Checklist
- [ ] Create pull request
- [ ] Code review completed
- [ ] All tests passing in CI/CD
- [ ] Documentation updated
- [ ] Changelog updated

### ✅ Step 15.2: Deployment
- [ ] Merge to main branch
- [ ] Deploy to staging environment
- [ ] Run smoke tests in staging
- [ ] Deploy to production
- [ ] Monitor for errors

### ✅ Step 15.3: Post-Deployment
- [ ] Verify all services running
- [ ] Check error logs
- [ ] Monitor performance metrics
- [ ] Verify strategy execution works
- [ ] Verify API endpoints work

---

## Rollback Plan

If issues arise during migration:

1. **Immediate Rollback:**
   - [ ] Revert to previous commit
   - [ ] Redeploy previous version
   - [ ] Verify services are working

2. **Partial Rollback:**
   - [ ] Keep shared package
   - [ ] Restore duplicate files temporarily
   - [ ] Update imports back to original paths
   - [ ] Fix issues incrementally

3. **Investigation:**
   - [ ] Review error logs
   - [ ] Identify root cause
   - [ ] Create fix plan
   - [ ] Re-attempt migration

---

## Success Criteria

- ✅ All tests passing (backend, trading-engine, worker, shared)
- ✅ No duplicate code between backend and trading-engine
- ✅ All services start successfully
- ✅ Strategy execution works correctly
- ✅ Broker operations work correctly
- ✅ Data provider operations work correctly
- ✅ No performance degradation
- ✅ Documentation updated
- ✅ Code coverage maintained

---

## Estimated Timeline

| Phase | Estimated Time | Dependencies |
|-------|---------------|--------------|
| Phase 0: Preparation | 2 hours | None |
| Phase 1: Create Structure | 1 hour | Phase 0 |
| Phase 2: Schemas & Symbols | 2 hours | Phase 1 |
| Phase 3: Broker Providers | 3 hours | Phase 2 |
| Phase 4: Data Providers | 3 hours | Phase 2 |
| Phase 5: Signal Models | 1 hour | Phase 1 |
| Phase 6: Strategy Infrastructure | 2 hours | Phase 5 |
| Phase 7: Indicator Strategies | 2 hours | Phase 6 |
| Phase 8: Intraday Strategies | 2 hours | Phase 6 |
| Phase 9: Swing Strategies | 1 hour | Phase 6 |
| Phase 10: Update Backend | 4 hours | Phases 3-9 |
| Phase 11: Update Trading-Engine | 4 hours | Phases 3-9 |
| Phase 12: Update Worker | 1 hour | Phases 3-9 |
| Phase 13: Integration Testing | 4 hours | Phases 10-12 |
| Phase 14: Documentation | 2 hours | Phase 13 |
| Phase 15: Deployment | 2 hours | Phase 14 |
| **TOTAL** | **36 hours (~4.5 days)** | |

---

## Notes

- Test frequently after each phase
- Commit after each successful phase
- Use feature flags if deploying incrementally
- Keep communication open with team
- Document any issues encountered
- Update this checklist as you progress


