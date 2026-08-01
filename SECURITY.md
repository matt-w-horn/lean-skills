# Security Policy

## Reporting a vulnerability

Report vulnerabilities privately through [GitHub's private vulnerability
reporting](https://github.com/matt-w-horn/lean-skills/security/advisories/new)
or by email to matt [at] matthorn [dot] io. Do not open public issues for
security reports.

This is a personal project, maintained on a best-effort basis. I will
acknowledge reports as quickly as I can, usually within a few days.

## Scope

This repository contains Markdown instructions for AI coding agents. It ships
no executable code beyond two standard-library Python scripts exercised in CI
(the validator and the claims-review sweep renderer), and it has no runtime
dependencies. The most plausible issue here is a skill file that instructs an
agent to run something harmful. Reports of that kind are in scope and welcome.
