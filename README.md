# CI Workflow Test

Test repo for validating the bridge CI pipeline before deploying to the customer repo.

## Testing steps

1. Push this repo to your personal GitHub
2. Create a `develop` branch and push it
3. Create a feature branch, make a change under `src/sparkplugb-bridge/`
4. Open a PR targeting `develop`
5. Verify the workflow runs: pytest, coverage PR comment, ruff lint
