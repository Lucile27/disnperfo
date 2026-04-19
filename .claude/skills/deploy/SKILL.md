---
name: deploy
description: Use when the user wants to deploy the web site to production. Runs deploy.sh and verifies key pages return HTTP 200.
---

Deploy web changes to production.

Steps:
1. Run `bash deploy.sh` (or the project's deploy script)
2. Verify key pages return HTTP 200:
   - `curl -s -o /dev/null -w "%{http_code}" https://example.com/`
3. Report results in a summary table.
4. If any page fails, investigate and report.
