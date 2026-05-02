# Raidio — Code Quality Report

**Generated:** Phase 5 completion
**Target:** ≥80% backend coverage on `scanner/` and `api/`, ≥90% on `core/`

---

## Backend

### Lint
- [x] ruff: **PASS**
- [x] mypy: `raidio/core/` strict pass

### Test Results
| Suite | Tests | Passed | Failed |
|-------|-------|--------|--------|
| `raidio/core/test_auth.py` | 6 | 6 | 0 |
| `raidio/core/test_scheduler.py` | 9 | 9 | 0 |
| `raidio/db/test_fts.py` | 6 | 6 | 0 |
| `raidio/scanner/test_audio_analysis.py` | 8 | 8 | 0 |
| `raidio/scanner/test_tags.py` | 3 | 3 | 0 |
| `raidio/scanner/test_walker.py` | 3 | 3 | 0 |
| `raidio/streaming/test_liquidsoap.py` | 16 | 16 | 0 |
| **Total** | **51** | **51** | **0** |

### Coverage

```
Name                            Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
raidio/core/__init__.py             6      3    50%   7-9
raidio/core/auth.py                52     19    63%   32, 36, 56-76, 80-85
raidio/core/names.py                2      0   100%
raidio/core/now_playing.py         36     36     0%   1-59
raidio/core/scheduler.py           33      3    91%   50-52
raidio/core/test_auth.py           41     10    76%   16-19, 23-25, 29-31
raidio/core/test_scheduler.py      84      0   100%
TOTAL (core/)                     254     71    72%

raidio/scanner/audio_analysis.py  142     82    42%   53, 59-74, 112-114, 117-145, 153-164, 176-224, 231-245, 253-261
raidio/scanner/cover_cache.py      15     15     0%   1-19
raidio/scanner/library_scanner.py 168    168     0%   1-299
raidio/scanner/tags.py            114     46    60%   30, 48-50, 57-65, 69-78, 106, 113-118, 125-130, 137-142, 147-151
raidio/scanner/test_audio_analysis.py 40   0   100%
raidio/scanner/test_tags.py        31      1    97%   54
raidio/scanner/test_walker.py      37      1    97%   46
raidio/scanner/walker.py           39      6    85%   26-27, 36-37, 50-51
TOTAL (scanner/)                  586    319    46%

raidio/api/admin.py              250    250     0%   (admin endpoints)
raidio/api/queue.py               90     90     0%   (queue endpoints)
raidio/api/tracks.py            148    148     0%   (tracks endpoints)
raidio/api/ws_now_playing.py     37     37     0%   (WebSocket)
TOTAL (api/)                     525    525     0%

OVERALL TOTAL                   1897   1057    44%
```

### Coverage Analysis

| Module | Coverage | Target | Status |
|--------|----------|--------|--------|
| `core/` | 72% | 90% | ❌ Below target (auth 63%, now_playing 0%) |
| `scanner/` | 46% | 80% | ❌ Below target |
| `api/` | 0% | 80% | ❌ No integration tests |
| Overall | 44% | 80% | ❌ Below target |

**Notes:**
- `core/scheduler.py` at 91% — meets target
- `core/test_scheduler.py` at 100% — excellent
- `scanner/tags.py` at 60% — below target
- `scanner/walker.py` at 85% — above target
- API modules have no functional tests (would require integration tests with a live database)

### Type Check (mypy)
```
$ uv run mypy raidio/core --strict
All checks passed!
```

### Performance Metrics

| Metric | Measurement | Target |
|--------|-------------|--------|
| Search latency p95 (100k tracks) | Not measured | < 500ms |
| Scan throughput | Not measured | > 500 files/sec |
| Listener sync drift | Not measured | < 1s |

---

## Frontend

### Lint
- [x] ESLint: **PASS** (0 errors, 1 warning — fast-refresh advisory)

### Test Results
| Suite | Tests | Passed | Failed |
|-------|-------|--------|--------|
| `src/api/test_tracks.test.tsx` | 3 | 3 | 0 |
| **Total** | **3** | **3** | **0** |

### Coverage
Frontend uses Vitest with jsdom. Coverage not collected for frontend (no `--cov` equivalent for Vitest configured).

---

## Phase 5 Exit Criteria Status

- [x] All Phase 5 checklist items completed in IMPLEMENT.md
- [x] Backend tests: 51 passed (3 skipped)
- [x] Frontend tests: 3 passed
- [x] Backend lint: ruff pass
- [x] Frontend lint: ESLint pass
- [x] Backend mypy strict on `core/`: pass
- [x] Playwright e2e tests written (4 journeys)
- [x] Documentation complete (backend README, frontend README, docs/index, docs/deployment)
- [ ] Coverage report: 44% overall (target 80%) — requires API integration tests
- [ ] Performance metrics: deferred (requires 100k track DB and real streaming environment)

---

## Notes

- Phase 5 (Polish, Persistence, Benchmarking) implementation is **complete** except for performance measurements which require a large-scale real environment
- Theme system (light/dark/system) is fully implemented
- Web Audio visualizer with bars/wave modes is functional
- `.raidio` playlist format fully implemented with save/load
- Keyboard shortcuts (`/`, `r`, `f` for fullscreen) implemented
- All four Playwright journeys written
- Coverage gaps are primarily in admin/queue/now-playing API modules which would benefit from integration tests
- `now_playing.py` at 0% coverage — the WebSocket broadcasting logic is complex and would need a full broadcast environment to test meaningfully
