# Signal Sciences Integration

This integration provides a SOAR (Security Orchestration, Automation, and Response) interface for Signal Sciences (Fastly Next-Gen WAF).

## Features
- Connectivity test (Ping)
- Add IP to Allow/Block lists
- Remove IP from Allow/Block lists

## Actions
### Ping
Tests the connectivity and authentication credentials.

### Add IP to AllowList
Adds a single IP or comma-separated IPs to the Signal Sciences allowlist. Can also process IPs from the SOAR context entities.

### Remove IP from AllowList
Removes IPs from the Signal Sciences allowlist.

### Add IP to BlockList
Adds IPs to the Signal Sciences blocklist.

### Remove IP from BlockList
Removes IPs from the Signal Sciences blocklist.
