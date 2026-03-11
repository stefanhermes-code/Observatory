# GitHub – Commit instructions for Live Alignment

Ensure the following are committed and pushed to the PU Observatory GitHub repo.

## Files to add and commit

| File | Purpose |
|------|---------|
| `core/generator_execution.py` | Phase 5 HTML path; filter candidates before extraction; USE_PHASE5_REPORT from secrets in phased flow |
| `core/intelligence_report.py` | Strict customer filter (unset metadata does not pass when dimension constrained) |
| `configurator_app.py` | report_period in spec and in report_options on submit |
| `PU_OBSERVATORY_LIVE_ALIGNMENT_STATUS.md` | Implementation status vs plan |
| `PU_OBSERVATORY_LIVE_ALIGNMENT_PACK/` | §19 validation checklist + §20 implementation package (README, code list) |

## Commands (PowerShell, run from repo root)

```powershell
Set-Location "C:\Users\Stefan Hermes\OneDrive - Foam Innovations & Solutions\Documenten\Bedrijven\HTC\PRODUCTS\12. Polyurethane Observatory"

git add core/generator_execution.py core/intelligence_report.py configurator_app.py
git add PU_OBSERVATORY_LIVE_ALIGNMENT_STATUS.md
git add PU_OBSERVATORY_LIVE_ALIGNMENT_PACK/
git status
git commit -m "Live alignment: Phase 5 HTML path, strict filter, report_period, §19-20 deliverables"
git push origin main
```

## Zip package (§20)

To create **PU_OBSERVATORY_LIVE_ALIGNMENT_PACK.zip** for delivery:

```powershell
Compress-Archive -Path "PU_OBSERVATORY_LIVE_ALIGNMENT_PACK\*" -DestinationPath "PU_OBSERVATORY_LIVE_ALIGNMENT_PACK.zip"
```

The zip contains: VALIDATION_CHECKLIST_S19.md, README_IMPLEMENTATION_PACKAGE.md, CODE_CHANGES_LIST.txt.
