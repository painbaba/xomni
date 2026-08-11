---
name: Bug report
about: Report a bug in XOMNI so we can fix it
title: "[Bug]: "
labels: ["bug", "triage"]
assignees: []
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to report a bug. Please fill in as much as
        you can — complete reports get fixed faster.
  - type: textarea
    id: description
    attributes:
      label: Describe the bug
      description: What happened, and what did you expect to happen?
      placeholder: "A clear, concise description of the bug."
    validations:
      required: true
  - type: textarea
    id: repro
    attributes:
      label: Steps to reproduce
      description: Exact steps, including any commands, tool invocations, or slash commands used.
      placeholder: |
        1. Run `bash .bench/run_all_tests.sh`
        2. Invoke /some-command ...
        3. See error ...
      render: bash
    validations:
      required: true
  - type: dropdown
    id: component
    attributes:
      label: Affected component
      description: Which part of XOMNI is affected?
      options:
        - Plugin (specify name in the field below)
        - data/build_db.py / skill scanning
        - Website
        - Core / runtime loop
        - Docs
        - Other
    validations:
      required: true
  - type: input
    id: plugin-name
    attributes:
      label: Plugin name (if a plugin is affected)
      description: e.g. context-loader, gh-ops, repomap
    validations:
      required: false
  - type: textarea
    id: logs
    attributes:
      label: Relevant logs / error output
      description: Paste error messages, tracebacks, or test failures. Redact any secrets.
      render: shell
    validations:
      required: false
  - type: textarea
    id: environment
    attributes:
      label: Environment
      description: OS, Python version, shell (git-bash/PowerShell), commit or version.
      placeholder: |
        - OS: Windows 11
        - Python: 3.11
        - Shell: git-bash
        - Commit: <sha or version>
    validations:
      required: true
  - type: checkboxes
    id: checks
    attributes:
      label: Checklist
      options:
        - label: I searched existing issues and this is not a duplicate
          required: true
        - label: I have redacted any secrets/API keys from this report
          required: true
        - label: I confirm this is not a security vulnerability (if it is, I reported it via SECURITY.md instead)
          required: true
---
