# Raidio — Code Quality Report

**Generated:** Phase 2 completion
**Target:** ≥80% backend coverage on `scanner/` and `api/`, ≥90% on `core/`

---

## Backend

### Lint
- [x] ruff: **PASS**
- [x] mypy: Errors present (see below)

### Test Results
| Suite | Tests | Passed | Failed |
|-------|-------|--------|--------|
| `raidio/streaming/test_liquidsoap.py` | 16 | 16 | 0 |
| `raidio/db/test_fts.py` | 6 | 6 | 0 |
| `raidio/scanner/test_tags.py` | 3 | 3 | 0 |
| `raidio/scanner/test_walker.py` | 3 | 3 | 0 |
| **Total** | **28** | **28** | **0** |

### Coverage
```
# TODO(phase3): Run with: uv run pytest --cov=raidio --cov-report=term-missing
```

### Type Check (mypy)
```
# TODO(phase4): Address mypy errors in Phase 4
```

---

## Frontend

### Lint
- [x] ESLint: **PASS**

### Test Results
| Suite | Tests | Passed | Failed |
|-------|-------|--------|--------|
| `src/api/test_tracks.test.tsx` | 3 | 3 | 0 |
| **Total** | **3** | **3** | **0** |

---

## Phase 2 Exit Criteria Status

- [x] All Phase 2 checklist items completed in IMPLEMENT.md
- [x] Backend tests: 28 passed
- [x] Frontend tests: 3 passed
- [x] Backend lint: ruff pass
- [x] Frontend lint: ESLint pass
- [ ] Coverage report: Not yet measured (deferred to Phase 5.7)
- [ ] Search latency measurement: Not yet measured (deferred to Phase 5.7)
- [ ] Scan throughput measurement: Not yet measured (deferred to Phase 5.7)

---

## Notes

- Phase 2 (Library Scanner & Catalog) implementation is **complete**
- WebSocket for scan progress is wired but not fully tested end-to-end
- Frontend routing is set up with react-router-dom
- Auth (JWT) is TODO(phase4) as specified