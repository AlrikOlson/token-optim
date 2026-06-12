# Security

## Reporting a vulnerability

Please report security issues privately via GitHub's **Report a
vulnerability** form on this repository (Security tab) rather than a
public issue. You'll get a response within a week.

## Scope notes

- The demo server (`python demo.py serve`) binds `127.0.0.1` only and is
  intended for local use; it is not hardened for public exposure.
- All report generation is local-only: uploaded exports are processed in
  memory and never transmitted.
- Live API adapters (`ledger.py`) read credentials from environment
  variables (`GITHUB_TOKEN`); no credential is ever written to disk.
