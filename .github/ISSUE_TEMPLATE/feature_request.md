---
name: Feature request
about: Suggest a new plugin, tool, command, or improvement for XOMNI
title: "[Feature]: "
labels: ["enhancement"]
assignees: []
body:
  - type: markdown
    attributes:
      value: |
        Thanks for suggesting a feature! Please describe the problem you're
        solving — proposals that explain the "why" get prioritized.
  - type: textarea
    id: problem
    attributes:
      label: Problem statement
      description: What problem does this solve? What can't you do today?
      placeholder: "When I ..., I can't ... because ..."
    validations:
      required: true
  - type: textarea
    id: proposal
    attributes:
      label: Proposed solution
      description: Describe the feature — a new plugin, tool, slash command, or change. If it's a plugin, sketch the anatomy per CONTRIBUTING.md (plugin.yaml, register(ctx) tools/commands, core.py logic).
      placeholder: "A new plugin `my-tool` that ... Tools: ..., Commands: /..."
    validations:
      required: true
  - type: dropdown
    id: component
    attributes:
      label: Affected component
      description: Where does this belong?
      options:
        - New plugin
        - Existing plugin (specify in the field below)
        - Core / runtime loop
        - Website
        - Docs
        - Other
    validations:
      required: true
  - type: input
    id: plugin-name
    attributes:
      label: Plugin name (if modifying an existing plugin)
      description: e.g. context-loader, gh-ops, repomap
    validations:
      required: false
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
      description: What workarounds or alternatives have you tried?
    validations:
      required: false
  - type: checkboxes
    id: checks
    attributes:
      label: Compatibility checklist
      options:
        - label: I confirm this adds zero hooks and keeps the <1s per-turn speed target (see CONTRIBUTING.md)
          required: false
        - label: I searched existing issues/PRs and this is not a duplicate
          required: true
---
