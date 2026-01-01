# Deep Dive: Playbook Structure

## Playbook Structure Guide

This document outlines the standard folder structure and file contents for creating a new playbook.
Playbooks are located in one of two directories:

- `content/playbooks/third_party/community` for community-contributed playbooks.
- `content/playbooks/third_party/partner` for partner-supported playbooks.

All playbooks, whether community or partner, follow the same internal structure described below.

**Note:** All file names must be in snake_case

## Folder Structure

A playbook is placed inside either the `community` or `partner` directory. The `playbook_name`
folder itself has the following structure:

```
repository
└── playbook_name/
    ├── steps/
    │   ├── step1.yaml
    │   ├── step2.yaml
    │   └── ...
    ├── widgets/
    │   ├── widget1.html
    │   ├── widget1.yaml
    │   ├── widget2.html
    │   ├── widget2.yaml
    │   └── ...
    ├── definition.yaml
    ├── display_info.yaml
    ├── overviews.yaml
    ├── release_notes.yaml
    └── trigger.yaml
```

## File Contents and Purpose

### Root Level Files

- **`definition.yaml`**: Contains metadata about the playbook.
- **`display_info.yaml`**: Contains information about how the playbook is displayed in the
  Content-Hub.
- **`overviews.yaml`**: Contains overview information for the playbook.
- **`release_notes.yaml`**: Documents changes for each version:
    - Version numbers
    - Release dates (in YYYY-MM-DD format)
    - Description of changes
    - Bug fixes
    - New features
- **`trigger.yaml`**: Defines the trigger for the playbook.

### steps/ Directory

The `steps/` directory contains all the steps that are part of the playbook:

- **`step_name*.yaml`**: YAML definition files for each step, including their parameters and logic.

### widgets/ Directory

The `widgets/` directory contains all the widgets that the playbook provides:

- **`widget_name*.html`**: HTML files for each widget.
- **`widget_name*.yaml`**: YAML definition files for each widget.
