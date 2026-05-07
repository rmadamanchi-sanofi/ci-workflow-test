# SiteWise CI/CD Demo

Automated pipeline for deploying SiteWise models and assets from Ignition JSON definitions.

## Architecture

```
ignition branch → develop → release/{site}/v{x} → main
   (upload)        (Dev)        (Test)              (Prod)
```

## Folder Structure

```
models/                    ← Ignition UDT JSON files (central team)
assets/
  waterford/               ← Per-site asset JSON files
  dublin/
scripts/
  generate_sitewise_tf.py  ← Generator script
projects/sitewise/         ← Auto-generated Terraform output
  models/
  waterford/
  dublin/
```

## Workflow

1. Ignition pushes JSON to `ignition` branch
2. Generate workflow validates, generates Terraform, merges to `develop`
3. Deploy workflow triggers on `develop` → deploys to Dev (auto)
4. Release branch auto-created → deploys to Test (manual approval)
5. Merge to `main` → deploys to Prod (manual approval)
