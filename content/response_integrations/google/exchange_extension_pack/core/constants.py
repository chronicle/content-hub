from __future__ import annotations
PROVIDER_NAME = "Exchange Extension Pack"

# Actions
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
RUN_COMPLIANCE_SEARCH_SCRIPT_NAME = f"{PROVIDER_NAME} - Run Compliance Search"
FETCH_COMPLIANCE_SEARCH_RESULTS_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - Fetch Compliance Search Results"
)
PURGE_COMPLIANCE_SEARCH_RESULTS_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - Purge Compliance Search Results"
)
DELETE_COMPLIANCE_SEARCH_SCRIPT_NAME = f"{PROVIDER_NAME} - Delete Compliance Search"
ADD_SENDERS_TO_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULE_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - Add Senders to Exchange-Siemplify Mail Flow Rule"
)
REMOVE_SENDERS_FROM_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - Remove Senders from Exchange-Siemplify Mail Flow Rules"
)
ADD_DOMAINS_TO_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - Add Domains to Exchange-Siemplify Mail Flow Rules"
)
REMOVE_DOMAINS_FROM_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - Remove Domains from Exchange-Siemplify Mail Flow Rules"
)
LIST_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - List Exchange-Siemplify Mail Flow Rules"
)
DELETE_EXCHANGE_SIEMPLIFY_MAIL_FLOW_RULES_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - Delete Exchange-Siemplify Mail Flow Rules"
)


# Commands
COMMANDS = {
    "test_connectivity_on_prem": "Remove-PSSession $Session}}",
    "test_connectivity_o365": "",
    "create_compliance_search_on_prem": 'New-ComplianceSearch "{compliance_search_name}" -ExchangeLocation {location} -ContentMatchQuery "{query}" -Force; Start-ComplianceSearch "{compliance_search_name}"; Remove-PSSession $Session}}',
    "create_compliance_search_o365": 'New-ComplianceSearch "{compliance_search_name}" -ExchangeLocation {location} -ContentMatchQuery "{query}" -Force; Start-ComplianceSearch "{compliance_search_name}"',
    "get_compliance_search_status_on_prem": 'Get-ComplianceSearch "{compliance_search_name}" | ConvertTo-Json; Remove-PSSession $Session}} | Out-File -FilePath {file_name}',
    "get_compliance_search_status_o365": 'Get-ComplianceSearch "{compliance_search_name}" | ConvertTo-Json | Out-File -FilePath {file_name}',
    "create_compliance_search_preview_on_prem": 'New-ComplianceSearchAction -SearchName "{compliance_search_name}"  -Preview -Confirm:$false; Remove-PSSession $Session}}',
    "create_compliance_search_preview_o365": 'New-ComplianceSearchAction -SearchName "{compliance_search_name}"  -Preview -Confirm:$false;',
    "get_compliance_search_preview_on_prem": 'Get-ComplianceSearchAction  -Identity "{compliance_search_name}_Preview" -Details -IncludeCredential | ConvertTo-Json | Format-List; Remove-PSSession $Session}} | Out-File -FilePath {file_name}',
    "get_compliance_search_preview_o365": 'Get-ComplianceSearchAction  -Identity "{compliance_search_name}_Preview" -Details -IncludeCredential | ConvertTo-Json | Out-File -FilePath {file_name} | Format-List',
    "remove_compliance_search_on_prem": 'Remove-ComplianceSearch -Confirm:$false "{compliance_search_name}"; Remove-PSSession $Session}}',
    "remove_compliance_search_o365": 'Remove-ComplianceSearch -Confirm:$false "{compliance_search_name}"',
    "create_compliance_search_purge_on_prem": 'New-ComplianceSearchAction -Confirm:$false -SearchName "{compliance_search_name}" -Purge; Remove-PSSession $Session}}',
    "create_compliance_search_purge_o365": 'New-ComplianceSearchAction -Confirm:$false -SearchName "{compliance_search_name}"  -Purge -PurgeType {state}',
    "get_compliance_search_purge_on_prem": 'Get-ComplianceSearchAction  -Identity "{compliance_search_name}_Purge" -Details -IncludeCredential | ConvertTo-Json | Format-List; Remove-PSSession $Session}} | Out-File -FilePath {file_name}',
    "get_compliance_search_purge_o365": 'Get-ComplianceSearchAction  -Identity "{compliance_search_name}_Purge" -Details -IncludeCredential | ConvertTo-Json | Out-File -FilePath {file_name} | Format-List',
    "get_mail_flow_rules_on_prem": "Get-TransportRule | ConvertTo-Json; Remove-PSSession $Session}} | Out-File -FilePath {file_name}",
    "get_mail_flow_rules_o365": "Get-TransportRule | ConvertTo-Json | Out-File -FilePath {file_name}",
    "create_mail_flow_rule_on_prem": 'New-TransportRule -Name "{rule_name}" {condition} {items} {action}; Remove-PSSession $Session}}',
    "create_mail_flow_rule_o365": 'New-TransportRule -Name "{rule_name}" {condition} {items} {action}',
    "update_mail_flow_rule_on_prem": 'Set-TransportRule "{rule_name}" {condition} {items}; Remove-PSSession $Session}}',
    "update_mail_flow_rule_o365": 'Set-TransportRule "{rule_name}" {condition} {items}',
    "delete_mail_flow_rule_on_prem": 'Remove-TransportRule -Confirm:$false "{rule_name}"; Remove-PSSession $Session}}',
    "delete_mail_flow_rule_o365": 'Remove-TransportRule -Confirm:$false "{rule_name}"',
}

ON_PREM_CONNECT_COMMAND = '$SiteServer = "{server_address}"; $securePassword = ConvertTo-SecureString "{password}" -AsPlainText -force; $credential = New-Object System.Management.Automation.PsCredential("{domain}\\{username}",$securePassword); $session = New-PSSession -computername {server_address} -credential $credential -Authentication Negotiate; Invoke-Command -Session $session -Scriptblock {{ $securePassword = ConvertTo-SecureString "{password}" -AsPlainText -force; $credential = New-Object System.Management.Automation.PsCredential("{domain}\\{username}",$securePassword); $pso = new-pssessionoption -skipcacheck -SkipCNCheck -SkipRevocationCheck; $Session= New-PSSession -Configuration Microsoft.Exchange -ConnectionUri https://{server_address}/PowerShell/  -Credential $credential -Authentication Basic -AllowRedirection -Sessionoption $pso; $import = Import-PSSession $Session; {command}'
O365_CONNECT_COMMAND = '$securePassword = ConvertTo-SecureString -String "{password}" -AsPlainText -Force; $credential = New-Object System.Management.Automation.PsCredential("{username}",$securePassword); $Session = Connect-IPPSSession -ConnectionUri {connection_uri}  -Credential $credential; {command}'
O365_DISCONNECT_COMMAND = "Disconnect-ExchangeOnline -Confirm:$false -WarningAction: SilentlyContinue 6>$null | Out-Null"


POWERSHALL_COMMAND = "pwsh"
ERROR_TEXTS = {
    "gss_failure": "GSS failure",
    "powershell": f"No such file or directory: '{POWERSHALL_COMMAND}'",
    "no_results": "didn't return any results",
    "not_found": ["cannot be found", "couldn't be found"],
    "already_exists": "already exists",
    "session_error": "Cannot validate argument on parameter 'Session'",
    "invalid_query": "The property keyword isn't supported",
}

COMPLETED_STATUS = "Completed"
RESULT_FILE_NAME = "result.json"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
QUERY_SPECIAL_CHARACTERS = ["'", '"']
SPECIAL_CHARACTERS = ["$"]

DELETE_STATE = {"hard_delete": "HardDelete", "soft_delete": "SoftDelete"}

PARAMETERS_DEFAULT_DELIMITER = ","

# Mail Flow Rules constants
RULES = {
    "domains_permanently_delete": "Siemplify - Domains List - Permanently Delete",
    "senders_permanently_delete": "Siemplify - Senders List - Permanently Delete",
}

DOMAIN_RULES = [RULES.get("domains_permanently_delete")]

SENDER_RULES = [RULES.get("senders_permanently_delete")]

ACTIONS = {
    RULES.get("domains_permanently_delete"): "-DeleteMessage $True",
    RULES.get("senders_permanently_delete"): "-DeleteMessage $True",
}

CONDITIONS = {"domain": "-FromAddressContainsWords", "sender": "-From"}

CORRESPONDING_RULES = {
    RULES.get("senders_permanently_delete"): RULES.get("domains_permanently_delete")
}

ALL_AVAILABLE_RULES_STRING = "All available Exchange-Siemplify Mail Flow Rules"

EMAIL_REGEX = r"[\w\d_.+-]+@([\w\d.-]+\.)+[\w.-]{2,}"
DOMAIN_REGEX = r"^([\w\d.-]+\.)+[\w.-]{2,}$"

# maximum retries count in case of network error
ASYNC_ACTION_MAX_RETRIES = 5
COMMAND_TIMEOUT = 240
