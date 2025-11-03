# Git Sync Integration

## Overview

The Git Sync integration provides bidirectional synchronization between SecOps and Git repositories. It enables teams to manage their SOAR content as code, providing version control, collaboration, and deployment automation for integrations, playbooks, and system configurations.

## Table of Contents

1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Installation & Configuration](#installation--configuration)
4. [Available Jobs](#available-jobs)
5. [Integration Instance Selection Logic](#integration-instance-selection-logic)
6. [Supported Content Types](#supported-content-types)
7. [Configuration Parameters](#configuration-parameters)
8. [Usage Examples](#usage-examples)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

## Features

- **Platform Versioning**: Version control for SecOps platforms configurations.
- **Bidirectional Sync**: Push content from SecOps to Git and pull content from Git to SecOps
- **Multiple Git Providers**: Support for GitHub, GitLab, BitBucket, and other Git providers
- **Content Support**: Sync integrations, playbooks, jobs, connectors, mappings, and system settings
- **Environment Management**: Handle multiple environments with intelligent instance mapping
- **Conflict Detection**: Identify and handle merge conflicts during synchronization
- **Caching**: Optimize performance with intelligent caching mechanisms

## Prerequisites

- secOps instance with appropriate permissions
- Git repository with read/write access
- Network connectivity between SecOps and Git provider
- Valid authentication credentials (API tokens, SSH keys, or username/password)

## Installation & Configuration

### 1. Integration Installation

1. Upload the Git Sync integration package to SecOps 
2. Install the integration through the marketplace or custom integration upload
3. Create an integration instance with the required configuration parameters

### 2. Configuration Parameters

| Parameter                      | Description                                       | Required | Default |
|--------------------------------|---------------------------------------------------|----------|---------|
| **Repo URL**                   | Git repository URL (HTTPS or SSH)                 | ✅ | - |
| **Branch**                     | Git branch to sync with                           | ✅ | `main` |
| **Git Server Fingerprint**     | Git Server Fingerprint (`SHA256:...` or `MD:...`) | ❌ | `None` |
| **Git Username**               | Username for Git authentication                   | ❌ | `None` |
| **Git Password/Token/SSH Key** | Authentication credential                         | ✅ | - |
| **Commit Author**              | Author information for commits                    | ❌ | `GitSync <gitsync@siemplify.co>` |
| **SOAR Username**              | SecOps username for API access                    | ❌ | - |
| **SOAR Password**              | SecOps password for API access                    | ❌ | - |
| **Siemplify Verify SSL**       | Verify SSL certificates for SOAR API              | ❌ | `true` |
| **Git Verify SSL**             | Verify SSL certificates for Git operations        | ❌ | `true` |

## Available Jobs

### Push Jobs (SecOps → Git)

| Job | Description | Key Parameters |
|-----|-------------|----------------|
| **Push Content** | Sync all selected content types to Git | Content type toggles, commit message |
| **Push Integration** | Push specific integration to Git | Integration name, commit message |
| **Push Playbook** | Push specific playbook to Git | Playbook name, commit message |
| **Push Job** | Push specific job to Git | Job name, commit message |
| **Push Mappings** | Push integration mappings to Git | Integration name, commit message |
| **Push Connectors** | Push connector configurations to Git | Environment filter, commit message |

### Pull Jobs (Git → SecOps)

| Job | Description | Key Parameters |
|-----|-------------|----------------|
| **Pull Content** | Sync all selected content types from Git | Content type toggles |
| **Pull Integration** | Install specific integration from Git | Integration whitelist |
| **Pull Playbook** | Install specific playbook from Git | Playbook whitelist, include blocks |
| **Pull Jobs** | Install specific jobs from Git | Job whitelist |
| **Pull Mappings** | Install integration mappings from Git | Source integration name |
| **Pull Connector** | Install connector configuration from Git | Connector name |

## Integration Instance Selection Logic

### Overview

When pulling playbooks from Git, the integration automatically assigns integration instances to playbook steps. This process is critical for ensuring playbooks function correctly in the target environment. The selection logic follows a hierarchical approach based on environment configuration and instance availability. There are limitations to the matching, especially when using the integration to sync between different server instances.

### Selection Process Flow

```
1. Check for Existing Step Instance
   ↓
2. Determine Environment Strategy
   ↓
3. Find Available Integration Instances
   ↓
4. Apply Selection Logic
   ↓
5. Configure Step Parameters
```

### Environment-Based Selection Strategy

#### Single Environment Playbooks

When a playbook is assigned to **one specific environment** (not "All Environments"):

```python
# Example: Playbook assigned to "Production" environment
environments = ["Production"]
```

**Selection Logic:**
1. **Primary Instance**: Search for instance with similar 'display name' configured in the environment
3. **Display Name Matching**: In the case there was not match, look for similar display name in the shared environment ("*")
4. **Fallback**: If no instance found, leave unassigned

**Configuration Result:**
- `IntegrationInstance`: Direct instance ID or first available instance
- `FallbackIntegrationInstance`: Fallback instance (if configured)

#### Multi-Environment or Shared Playbooks

When a playbook is assigned to **multiple environments** or **"All Environments"**:

```python
# Examples:
environments = ["*"]  # All Environments
environments = ["Env1", "Env2", "Env3"]  # Multiple environments
```

**Selection Logic:**
1. **Automatic Mode**: Set step to use "AutomaticEnvironment"
2. **Shared Instance Search**: Look for instances in the shared environment ("*")
3. **Fallback Assignment**: Assign the first shared instance as fallback

**Configuration Result:**
- `IntegrationInstance`: "AutomaticEnvironment"
- `FallbackIntegrationInstance`: First available shared instance

### Integration Instance Matching

The system searches for integration instances using flexible matching criteria:

#### Exact Match
```python
instance["integrationIdentifier"] == "VirusTotal"
```

#### Shared Prefix Match
```python
instance["integrationIdentifier"] == "Shared_VirusTotal"
```

This allows for shared instances that can be used across multiple environments, addressing the common pattern where shared instances are prefixed with "Shared_".

### Instance Search and Caching

#### Search Scope
- **Environment-Specific**: Search within the specified environment
- **Cross-Environment**: For shared playbooks, search the shared environment ("*")
- **Cached Results**: Instance lists are cached per environment for performance

#### Instance Validation
- Only **configured instances** (`isConfigured: true`) are considered
- Instances are sorted by name for consistent selection
- Invalid or unconfigured instances are filtered out

### Existing Step Reuse Logic

When updating an existing playbook, the system attempts to preserve instance assignments:

```python
if existing_step:
    # Copy instance configuration from existing step
    instance_id = existing_step.parameters["IntegrationInstance"].value
    fallback_id = existing_step.parameters["FallbackIntegrationInstance"].value
    
    # Apply to new step
    new_step.parameters["IntegrationInstance"].value = instance_id
    new_step.parameters["FallbackIntegrationInstance"].value = fallback_id
```

This ensures that manual instance assignments are preserved during playbook updates.

### Display Name Resolution

The system stores and attempts to resolve instance display names:

1. **Store Display Names**: When pushing playbooks, display names are stored in step parameters
2. **Resolve on Pull**: When pulling playbooks, the system attempts to find instances by display name
3. **Fallback to ID**: If display name resolution fails, fall back to direct instance assignment

### Common Scenarios and Behaviors

#### Scenario 1: Single Environment with Available Instance
- **Environment**: "Production"
- **Available Instances**: ["VirusTotal_Prod", "Shared_VirusTotal"]
- **Result**: Uses "VirusTotal_Prod" (environment-specific instance preferred)

#### Scenario 2: Single Environment with No Direct Instance
- **Environment**: "Development"  
- **Available Instances**: ["Shared_VirusTotal"] (in shared environment)
- **Result**: Uses "Shared_VirusTotal" due to shared prefix matching

#### Scenario 3: Multi-Environment Playbook
- **Environment**: ["*"] (All Environments)
- **Available Instances**: ["VirusTotal_Dev", "Shared_VirusTotal"]
- **Result**: 
  - `IntegrationInstance`: "AutomaticEnvironment"
  - `FallbackIntegrationInstance`: "Shared_VirusTotal"

#### Scenario 4: Missing Environment on Target System
- **Source Environment**: "Staging" (doesn't exist on target)
- **Available Instances**: ["VirusTotal_Prod", "Shared_VirusTotal"]
- **Result**: May fail to find appropriate instance, requiring manual configuration

### Troubleshooting Instance Selection

#### Common Issues

1. **Instance Not Found**
   - **Cause**: No configured instances for the integration in target environment
   - **Solution**: Create and configure integration instance in target environment

2. **Wrong Instance Selected**
   - **Cause**: Multiple instances available, system selects first alphabetically
   - **Solution**: Use shared instances with "Shared_" prefix or ensure consistent naming

3. **Cross-Server Migration Issues**
   - **Cause**: Environment names differ between source and target systems
   - **Solution**: Create matching environments or use shared instances

4. **Playbook Step Unassigned**
   - **Cause**: Instance exists but is not configured (`isConfigured: false`)
   - **Solution**: Complete integration instance configuration

#### Debugging Tips

1. **Check Integration Instances**: Verify instances exist and are configured in target environment
2. **Review Environment Assignment**: Ensure playbook environment assignment matches available environments
3. **Use Shared Instances**: For cross-environment compatibility, use instances with "Shared_" prefix
4. **Check Instance Names**: Ensure consistent naming conventions across environments
5. **Review Logs**: Check SecOps logs for instance selection details and errors

## Supported Content Types

| Content Type | Push | Pull | Description |
|--------------|------|------|-------------|
| **Integrations** | ✅ | ✅ | Custom and commercial integrations |
| **Playbooks** | ✅ | ✅ | Workflows and automation blocks |
| **Jobs** | ✅ | ✅ | Scheduled jobs and automation |
| **Connectors** | ✅ | ✅ | Data ingestion connectors |
| **Visual Families** | ✅ | ✅ | Custom entity families |
| **Mappings** | ✅ | ✅ | Field mapping rules |
| **Simulated Cases** | ✅ | ✅ | Test cases for playbooks |

## Usage Examples

### Basic Sync Workflow

1. **Initial Setup**: Push existing content to establish baseline
2. **Development**: Make changes in SecOps
3. **Commit Changes**: Use Push jobs to sync changes to Git
4. **Review & Merge**: Review changes in Git, merge to main branch
5. **Deploy**: Use Pull jobs to deploy to other environments

### Cross-Environment Deployment

```bash
# Development Environment
1. Develop playbook in Dev environment
2. Push playbook: "Push Playbook" job
3. Commit to feature branch in Git

# Production Environment  
1. Merge feature branch to main
2. Pull playbook: "Pull Playbook" job
3. Verify instance assignments
4. Test playbook functionality
```

### Integration Instance Management

```bash
# Ensure Consistent Instance Names
Development: "VirusTotal_Dev"
Staging: "VirusTotal_Stage"  
Production: "VirusTotal_Prod"
Shared: "Shared_VirusTotal" (for cross-env playbooks)
```

## Best Practices

### Instance Naming Conventions

1. **Environment-Specific**: Use environment suffix (`IntegrationName_EnvName`)
2. **Shared Instances**: Use "Shared_" prefix for cross-environment instances
3. **Consistent Naming**: Maintain consistent naming patterns across environments

### Environment Strategy

1. **Single Environment**: Use for environment-specific playbooks
2. **All Environments**: Use for playbooks that should work across all environments
3. **Shared Instances**: Create shared instances for cross-environment compatibility

### Repository Management

1. **Branch Strategy**: Use feature branches for development, main for production
2. **Commit Messages**: Use descriptive commit messages for tracking changes
3. **Regular Sync**: Establish regular sync schedules for content synchronization

### Security Considerations

1. **Credential Management**: Use secure credential storage (tokens, SSH keys)
2. **Access Control**: Limit repository access to authorized personnel
3. **SSL Verification**: Enable SSL verification for production environments
4. **Audit Trail**: Maintain commit history for compliance and auditing

## Troubleshooting

### Common Issues

| Issue | Cause                                               | Solution |
|-------|-----------------------------------------------------|----------|
| Authentication Failed | Invalid credentials                                 | Verify Git credentials and permissions |
| Integration Instance Not Found | Missing instance in target environment (white list) | Create and configure integration instance |
| Playbook Import Failed | Missing dependencies                                | Ensure all required integrations are installed |
| SSL Certificate Error | Certificate validation issues                       | Check SSL settings and certificates |


**Version**: 32.0  
**Last Updated**: July 2025  