# SiteWise CI/CD Demo

Automated pipeline for deploying SiteWise models and assets from Ignition JSON definitions.

## Architecture

```
ignition branch (push) → generate TF → deploy to Dev (auto)
                       → create PR (release/{site}/vN → main)
                       → reviewer approves PR → deploy to Test
                       → merge PR → deploy to Prod
```

## Workflows

| File | Trigger | Does |
|------|---------|------|
| `generate-and-deploy-dev.yaml` | push to `ignition` | Validate JSON → Generate TF → Push to develop → Deploy Dev → Create release PR |
| `deploy-sitewise.yaml` | push to `release/**` or `main` | Deploy to Test/Prod, post plan to PR |

## Folder Structure

```
UDT [Models]/                  ← Ignition UDT JSON files (central team)
  UDTs.json
Sites/
  Core/UNS/tags.json           ← Shared/global asset definitions
  {SITE}/
    Pre-Prod/UNS [Assets]/     ← Per-site asset JSON files
    Prod/UNS [Assets]/
scripts/
  generate_sitewise_tf.py      ← Generator script (JSON → Terraform)
projects/sitewise/             ← Auto-generated Terraform output
  models/
  {SITE}/
```

## Sites

| Code | Name |
|------|------|
| WAT | Waterford |
| TOR | Toronto |
| LET | Lentilly |
| VAL | Valence |
| Core | Shared/Global |

## Approval Flow

- **Dev**: automatic (no approval needed)
- **Test**: PR review required (CODEOWNERS-based reviewers)
- **Prod**: PR merge to main required (CODEOWNERS-based reviewers)

## Requirements

- GitHub App (`sitewise-ci-bot`) for automated push from ignition → develop
- GitHub Environments: `dev`, `test`, `prod`
- Branch protection on `main` and `release/**`
