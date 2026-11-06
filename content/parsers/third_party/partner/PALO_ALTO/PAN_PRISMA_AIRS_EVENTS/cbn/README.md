# Palo Alto Networks Prisma AIRS Events

Google SecOps parser for [Palo Alto Networks Prisma AIRS (AI Runtime Security)](https://docs.paloaltonetworks.com/ai-runtime-security) API intercept events.

## Log Format

Events are forwarded by the Prisma AIRS Log Forwarding Service as RFC5424 syslog with a CEF payload, for example:

```
<134>1 2026-09-16T05:17:12.545Z <forwarder-host> logforwarder - panwlogs - CEF:0|Palo Alto Networks|LF|2.0|AI-SECURITY-API|regular|3|dtz=UTC rt=Aug 24 2026 00:58:06 ... PanOSAIIncidentType=ai-model-protection PanOSAIIncidentSubtype=prompt-injection PanOSVerdict=malicious PanOSAction=block
```

## Event Coverage

All events are mapped to `USER_RESOURCE_ACCESS`. The test data covers each AI incident subtype:

| Test case | Incident type | Incident subtype |
| :-- | :-- | :-- |
| `prompt_injection` | ai-model-protection | prompt-injection |
| `toxic_content` | ai-model-protection | toxic-content |
| `agent_security` | ai-model-protection | agent-security |
| `dlp` | ai-data-protection | dlp |
| `malicious_code` | ai-application-protection | malicious-code |
| `url_security` | ai-application-protection | url-security |
| `ai_traffic_type` | ai-traffic | (none) |

## Key UDM Mappings

| Source field | UDM field |
| :-- | :-- |
| `PanOSAIApplicationUserName` | `principal.user.userid` |
| `PanOSAPIKeyName` | `principal.user.product_object_id` |
| `PanOSAIApplicationName` | `target.resource.name` |
| `PanOSAIAppCloudProvider` | `target.resource.attribute.cloud.environment` |
| `PanOSAIModelName` | `target.ai.display_name` |
| `PanOSAction` | `security_result.action` |
| `PanOSAIIncidentSubtype`, `PanOSAIIncidentType` | `security_result.category_details` |
| `PanOSAISecurityProfileID` / `PanOSAISecurityProfileName` | `security_result.rule_set` / `security_result.rule_set_display_name` |
| `PanOSScanID`, `PanOSScanSUBRequestID` | `metadata.product_log_id` |

## Log Type

A dedicated pre-built log type for this source is pending. Until it is available, create a custom log type in your SecOps instance and attach this parser to it.
