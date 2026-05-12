from __future__ import annotations
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

import sys
import random
import json
from urllib.parse import urlparse
import re
import uuid
from datetime import datetime

from ..core.constants import (INTEGRATION_NAME, ALERT_CONNECTOR_NAME, DEVICE_PRODUCT, VENDOR_NAME, PRODUCT_NAME, PROPERTY_KEY)
from ..core.bloodhound_manager import BloodhoundManager


# Function to generate a consistent context identifier for storing the latest dates
def get_domain_dates_context_identifier(siemplify:SiemplifyConnectorExecution, context_identifier_prefix:str="bloodhound_last_created_attack_paths_date_"):
    """
    Generate a consistent context identifier for storing latest dates for all domains
    :return: {str} The generated context identifier
    """
    identifier = siemplify.context.connector_info.identifier
    
    # Create the context identifier
    return f"{context_identifier_prefix}{identifier}"

def get_domain_last_created_dates(siemplify):
    """
    Read the latest created dates for all domains from the connector context
    :param siemplify: {siemplify} Siemplify object
    :return:{dict} Dictionary mapping domain names to their last update dates, or empty dict if not found
    """
    context_identifier = get_domain_dates_context_identifier(siemplify)
    property_key = PROPERTY_KEY
    
    siemplify.LOGGER.info(f"Reading last created date from context: {context_identifier}")
    
    try:
        # Get stored last created_at dates from context property
        last_dates_json = siemplify.get_connector_context_property(
            identifier= context_identifier,
            property_key= property_key
        )
        
        if not last_dates_json:
            siemplify.LOGGER.info("No previous created_at dates found")
            return {}
        
        # Parse JSON string to dictionary
        last_dates = json.loads(last_dates_json)
        siemplify.LOGGER.info(f"Loaded {len(last_dates)} domain created_at dates from context")
        return last_dates

    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read last created_at dates from context: {e}")
        siemplify.LOGGER.exception(e)
        return {}

def store_domain_last_created_dates(siemplify, data):
    """
    Store the latest update dates for all domains in the connector context
    :param siemplify: {siemplify} Siemplify object
    :param data: {dict} Dictionary mapping domain names to their last update dates
    """
    try:
        context_identifier = get_domain_dates_context_identifier(siemplify)
        property_key = PROPERTY_KEY
        
        # Convert dictionary to JSON string
        data_json_str = json.dumps(data)
        
        # Store the JSON string in the connector context
        siemplify.set_connector_context_property(
            identifier=context_identifier,
            property_key=property_key,
            property_value=data_json_str
        )
        
        siemplify.LOGGER.info(f"Successfully stored last update dates for {len(data)} domains")

    except Exception as e:
        siemplify.LOGGER.error(f"Failed storing domain last update dates, ERROR: {e}")
        siemplify.LOGGER.exception(e)

def extract_date_from_timestamp(timestamp_str):
    """
    Extract the date part from a timestamp string
    :param timestamp_str: {str} The timestamp string (e.g., "2025-04-23T01:14:57.385152Z")
    :return: {str} The date part in YYYY-MM-DD format
    """
    try:
        # Parse the timestamp string into a datetime object
        dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        # Extract just the date part in YYYY-MM-DD format
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        # If unable to parse, return None
        return None

def test_bloodhound_connection(bhe_manager, siemplify):
    """
    Test connection to BloodHound Enterprise server
    
    Args:
        bhe_manager: BloodHound Enterprise manager instance
        siemplify: Siemplify connector execution instance
        
    Returns:
        tuple: (success status, response)
    """
    siemplify.LOGGER.info("Starting BloodHound Enterprise connection test...")
    response = bhe_manager.test_connection()
    
    if response:
        siemplify.LOGGER.info("Connected successfully to BloodHound Enterprise.")
    else:
        siemplify.LOGGER.error("Connection failed. Possible invalid credentials or endpoint issue.")
        siemplify.LOGGER.error(f"Error details: {response}")
        
    return response

def get_available_domains(bhe_manager, siemplify):
    """
    Extract available domains from the response
    
    Args:
        bhe_manager: BloodHound Enterprise manager instance
        siemplify: Siemplify connector execution instance
        
    Returns:
        dict: Dictionary mapping domain IDs to domain information
    """
    siemplify.LOGGER.info("Fetching list of available domains from BloodHound Enterprise.")
    status, response = bhe_manager.get_available_domains()
    
    if not status:
        siemplify.LOGGER.error("Failed to fetch available domains")
        return {}
    
    res_domains = response.json()
    domains_data = res_domains.get('data', [])
    
    # Create a dictionary mapping domain IDs to their info
    domains = {domain['id']: domain for domain in domains_data if domain['collected'] == True}
    
    return domains

def collect_available_types(bhe_manager, domains, siemplify):
    """
    Collect available types for each domain and add them to domain info
    
    Args:
        bhe_manager: BloodHound Enterprise manager instance
        domains: Dictionary mapping domain IDs to domain information
        
    Returns:
        dict: Updated domains dictionary with available types
    """
    siemplify.LOGGER.info("Collecting available finding types for each domain...")
    for domain_id in domains:
        siemplify.LOGGER.info(f"Fetching finding types for domain: {domains[domain_id].get('name', domain_id)}")
        types = bhe_manager.get_available_types_for_domain(domain_id)
        domains[domain_id]['available_types'] = types

    return domains

def fetch_path_info(bhe_manager, domains, siemplify):
    """
    Fetch path metadata for each unique finding type, including:
    - Title
    - Short Remediation
    - Long Remediation

    Args:
        bhe_manager: BloodHound Enterprise manager instance
        domains: Dictionary mapping domain IDs to domain information
        siemplify: Siemplify connector execution instance

    Returns:
        dict: Dictionary mapping finding types to their path metadata
    """
    siemplify.LOGGER.info("Fetching path details for each unique finding type...")

    # Get all unique finding types across all domains
    unique_finding_types = set()
    for domain_info in domains.values():
        unique_finding_types.update(domain_info.get('available_types', []))

    siemplify.LOGGER.info(f"Found {len(unique_finding_types)} unique finding types to fetch details for.")

    path_details = {}
    for finding_type in unique_finding_types:
        try:
            title = bhe_manager.get_path_title(finding_type)
            short_description = bhe_manager.get_finding_type_short_description(finding_type)
            short_remediation = bhe_manager.get_finding_type_short_remediation(finding_type)
            long_remediation = bhe_manager.get_finding_type_long_remediation(finding_type)

            if not title:
                siemplify.LOGGER.error(f"Failed to fetch title for {finding_type}, using finding_type as fallback.")
                title = finding_type

            path_details[finding_type] = {
                "title": title,
                "short_remediation": short_remediation,
                "long_remediation": long_remediation,
                "short_description":short_description
            }
        except Exception as e:
            siemplify.LOGGER.error(f"Failed to fetch path details for {finding_type}: {e}")
            path_details[finding_type] = {
                "title": finding_type,
                "short_remediation": "",
                "long_remediation": "",
                "short_description":""
            }

    return path_details

def fetch_attack_path_details(bhe_manager, domains, siemplify, tenant_domain, is_test_run):
    """
    Fetch attack path details for each domain and finding type,
    using the last update date as a filter when available.
    Only returns attack paths that are newer than the stored last created_at date.
    
    Args:
        bhe_manager: BloodHound Enterprise manager instance
        domains: Dictionary mapping domain IDs to domain information
        siemplify: Siemplify connector execution instance
        tenant_domain: BloodHound Enterprise tenant domain
        is_test_run: Boolean indicating if this is a test run
        
    Returns:
        tuple: (attack path details dict, domain latest dates dict)
    """
    siemplify.LOGGER.info("Starting attack path fetch process across all domains and types...")

    attack_path_details = {}
    domain_attack_path_counts = {}
    domain_latest_dates = {}
    
    # Get the last created_at dates for all domains
    last_created_at_dates = {} if is_test_run else get_domain_last_created_dates(siemplify)
    siemplify.LOGGER.info(f"Loaded last known created_at timestamps: {last_created_at_dates}")

    for domain_id, domain_info in domains.items():
        domain_name = domain_info.get("name", "unknown")
        types = domain_info.get('available_types', [])
        domain_attack_path_counts[domain_name] = 0
        domain_latest_dates[domain_name] = last_created_at_dates.get(domain_name)  # Initialize with stored date
         
        # Get the last update date for this domain
        last_created_at_timestamp = last_created_at_dates.get(domain_name)
        
        if last_created_at_timestamp:
            siemplify.LOGGER.info(f"Using last created_at timestamp for domain {domain_name}: {last_created_at_timestamp}.")
        else:
            siemplify.LOGGER.info(f"No last created_at timestamp found for domain {domain_name}, will fetch all attack paths.")

        siemplify.LOGGER.info(f"Processing domain: {domain_name} with {len(types)} finding types.")

        for finding_type in types:
            skip = 0
            filtered_attack_paths = []  # Will store only newer attack paths

            while True:
                # Always fetch all attack paths (don't filter at API level)
                # This ensures we get all paths to properly find the newest timestamp
                page = bhe_manager.get_attack_path_details_page(
                    domain_id,
                    finding_type,
                    skip=skip,
                    created_at=last_created_at_timestamp
                )

                if not page:
                    break

                siemplify.LOGGER.info(f"Number of attack paths fetched even after giving created_at date is {len(page)}")
                
                # Filter attack paths based on created_at timestamp
                newer_paths = []
                for attack_path in page:
                    created_at = attack_path.get("created_at")
                    if created_at:
                        # Only include attack paths with newer created_at timestamps
                        if not last_created_at_timestamp or created_at > last_created_at_timestamp:
                            newer_paths.append(attack_path)
                            
                            # Update domain's latest timestamp if needed
                            if domain_latest_dates[domain_name] is None or created_at > domain_latest_dates[domain_name]:
                                domain_latest_dates[domain_name] = created_at
                
                # Add only the newer attack paths to our filtered list
                filtered_attack_paths.extend(newer_paths)
                
                # Prepare for next page
                skip += len(page)
            
            # Store only filtered attack paths that are newer than last created_at
            if filtered_attack_paths:
                attack_path_details[(domain_id, finding_type)] = filtered_attack_paths
                domain_attack_path_counts[domain_name] += len(filtered_attack_paths)
    
    siemplify.LOGGER.info(f"Domain {domain_name}: {domain_attack_path_counts.get(domain_name)} new attack paths found")
    siemplify.LOGGER.info(f"Latest created_at date for domain {domain_name}: {domain_latest_dates[domain_name]}") 
    return attack_path_details, domain_latest_dates

def create_alerts(attack_path_details, domains, attack_paths_info, tenant_domain, siemplify):
    """
    Create alert objects from attack path details with enriched path metadata.
    Will split alerts if they contain more than 500 events.
    """
    siemplify.LOGGER.info("Creating alert objects for newly fetched attack paths...")
    alerts = []
    url_parser = urlparse(tenant_domain)
    parsed_tenant_domain = url_parser.netloc or url_parser.path
    current_time = unix_now()
    MAX_EVENTS_PER_ALERT = 500  # Maximum number of events allowed per alert

    domain_path_groups = {}

    # Group by domain and path title
    for (domain_id, finding_type), attack_paths in attack_path_details.items():
        domain_name = domains.get(domain_id, {}).get("name", "unknown")
        path_info = attack_paths_info.get(finding_type, {})
        path_title = path_info.get("title", finding_type)

        if domain_name not in domain_path_groups:
            domain_path_groups[domain_name] = {}

        if path_title not in domain_path_groups[domain_name]:
            domain_path_groups[domain_name][path_title] = []

        for path in attack_paths:
            domain_path_groups[domain_name][path_title].append((finding_type, path))

    if not domain_path_groups:
        siemplify.LOGGER.info("No new attack paths found, skipping alert creation")
        return alerts

    siemplify.LOGGER.info(f"Found {len(domain_path_groups)} domains with new attack paths")        

    for domain_name, attack_paths_info_dict in domain_path_groups.items():
        for path_title, attack_paths_with_type in attack_paths_info_dict.items():
            if not attack_paths_with_type:
                continue

            finding_type = attack_paths_with_type[0][0]
            path_info = attack_paths_info.get(finding_type, {})
            short_remediation = path_info.get("short_remediation", "")
            long_remediation = path_info.get("long_remediation", "")
            short_description = path_info.get("short_description","")

            # Determine severity
            path_highest_severity = "low"

            # Calculate number of batches needed to stay under MAX_EVENTS_PER_ALERT limit
            total_paths = len(attack_paths_with_type)
            num_batches = (total_paths + MAX_EVENTS_PER_ALERT - 1) // MAX_EVENTS_PER_ALERT  # Ceiling division
            
            if num_batches > 1:
                siemplify.LOGGER.info(f"Splitting {path_title} in {domain_name} into {num_batches} alerts due to {total_paths} events exceeding limit of {MAX_EVENTS_PER_ALERT}")
            
            # Process each batch separately
            for batch_num in range(num_batches):
                start_idx = batch_num * MAX_EVENTS_PER_ALERT
                end_idx = min((batch_num + 1) * MAX_EVENTS_PER_ALERT, total_paths)
                batch_paths = attack_paths_with_type[start_idx:end_idx]
                
                # Create suffix for batched alerts
                batch_suffix = f" (Part {batch_num + 1}/{num_batches})" if num_batches > 1 else ""
                alert_name = f"{path_title} in {domain_name}"
                
                # Create unique ID for each batch
                unique_batch_id = str(uuid.uuid4()) if num_batches > 1 else ""
                alert_id = f"{parsed_tenant_domain}:{domain_name}"

                alert = AlertInfo()
                alert.display_id = f"{VENDOR_NAME}:{str(uuid.uuid4())}"
                alert.ticket_id = alert_id  
                alert.name = alert_name
                alert.sourceGroupIdentifier = domain_name
                alert.SourceDomain = domain_name
                alert.rule_generator = alert_id
                alert.start_time = current_time
                alert.end_time = current_time
                alert.priority = 60
                alert.device_vendor = VENDOR_NAME
                alert.device_product = PRODUCT_NAME
                alert.environment = siemplify.context.connector_info.environment
                alert.description = (
                    f"New attack paths detected in domain {domain_name} "
                    f"short_description: {short_description}"
                    f"Short remediation: {short_remediation}"
                )
                if num_batches > 1:
                    alert.description += f" (Part {batch_num + 1} of {num_batches}, contains paths {start_idx+1}-{end_idx} of {total_paths})"
                
                alert.device_event_class_id = alert_id
                alert.extensions = {
                    "DomainName": domain_name,
                    "PathTitle": path_title,
                    "AttackPathCount": len(batch_paths),
                    "TotalAttackPathCount": total_paths,
                    "CaseId": f"{parsed_tenant_domain}:{domain_name}",
                    "ShortRemediation": short_remediation,
                    "LongRemediation": long_remediation,
                    "Description": short_description,
                    "FindingType": finding_type
                }
                
                if num_batches > 1:
                    alert.extensions["BatchNumber"] = batch_num + 1
                    alert.extensions["TotalBatches"] = num_batches
                
                alert.case_tags = [path_title, domain_name]
                if num_batches > 1:
                    alert.case_tags.append(f"Batch {batch_num + 1}/{num_batches}")

                alert_severity = "low"

                for finding_type, item in batch_paths:
                    attack_id = item.get("id", "unknown")
                    severity = item.get("Severity", "low")
                    props = item.get("FromPrincipalProps") or item.get("Props") or {}

                    object_ids = (
                        list(filter(None, [
                            item.get("FromPrincipalProps", {}).get("objectid"),
                            item.get("ToPrincipalProps", {}).get("objectid")
                        ])) if "FromPrincipalProps" in item
                        else [item.get("Props", {}).get("objectid")] if item.get("Props", {}).get("objectid") else []
                    )

                    object_names = (
                        list(filter(None, [
                            item.get("FromPrincipalProps", {}).get("name"),
                            item.get("ToPrincipalProps", {}).get("name")
                        ])) if "FromPrincipalProps" in item
                        else [item.get("Props", {}).get("name")] if item.get("Props", {}).get("name") else []
                    )

                    alert_severity = severity if severity > alert_severity else alert_severity

                    event = {
                        "StartTime": alert.start_time,
                        "EndTime": alert.end_time,
                        "name": f"Attack Path {attack_id}",
                        "object_ids": ", ".join(object_ids),
                        "object_names": ", ".join(object_names),
                        "device_product": DEVICE_PRODUCT,
                        "attack_id": attack_id,
                        "domain": domain_name,
                        "base_url": tenant_domain,
                        "RemediationURL": f"{tenant_domain}/ui/remediation?findingType={finding_type}",
                        "path_title": path_title.strip(),
                        "finding_type": finding_type,
                        "details": json.dumps(item),
                        "DomainSID": item.get("DomainSID"),
                        "ImpactPercentage": round(float(item.get("ImpactPercentage", 0)) * 100, 2),
                        "ImpactCount": item.get("ImpactCount"),
                        "Severity": severity,
                        "ExposurePercentage": round(float(item.get("ExposurePercentage", 0)) * 100, 2),
                        "ExposureCount": item.get("ExposureCount"),
                        "AcceptedUntil": item.get("AcceptedUntil"),
                        "Accepted": item.get("Accepted"),
                        "Created at": item.get("created_at"),
                        "Updated at": item.get("updated_at"),
                        "ShortRemediation": short_remediation.strip(),
                        "LongRemediation": long_remediation.strip(),
                        "ShortDescription": short_description.strip()
                    }

                    event["Impacted Principal"] = item.get("Principal", item.get("ToPrincipal"))
                    event["Impacted Principal Kind"] = item.get("PrincipalKind", item.get("ToPrincipalKind"))
                    event["Impacted Principal Name"] = item.get("PrincipalName", item.get("ToPrincipalName"))
                    event["Impacted Principal Environment"] = item.get("Environment", item.get("ToEnvironment"))
                    event["Impacted Principal Object Id"] = (
                        item.get("ToPrincipalProps", {}).get("objectid") or
                        item.get("Props", {}).get("objectid")
                    )

                    if "FromPrincipal" in item:
                        event["Non Tier Zero Principal"] = item.get("FromPrincipal")
                        event["Non Tier Zero Principal Name"] = item.get("FromPrincipalName")
                        event["Non Tier Zero Principal Kind"] = item.get("FromPrincipalKind")
                        event["Non Tier Zero Principal Environment"] = item.get("FromEnvironment")
                        event["Non Tier Zero Principal Object Id"] = (
                            item.get("FromPrincipalProps", {}).get("objectid") or
                            item.get("Props", {}).get("objectid")
                    )


                    alert.Severity = alert_severity
                    alert.events.append(event)

                alerts.append(alert)

    siemplify.LOGGER.info("---- Domain-wise Alerts Created ----")
    domain_alert_counts = {}
    for alert in alerts:
        domain = alert.extensions.get("DomainName", "unknown")
        domain_alert_counts[domain] = domain_alert_counts.get(domain, 0) + 1

    for domain_name, count in domain_alert_counts.items():
        siemplify.LOGGER.info(f"Domain {domain_name}: {count} alerts created")

    siemplify.LOGGER.info(f"---- Total Alerts Generated: {len(alerts)} ----")

    return alerts

def filter_domains(domains, selected_domains, siemplify):
    """
    Filter domains based on user selection
    
    Args:
        domains (dict): Dictionary of available domains
        selected_domains (str): Comma-separated string of domain names to include
        siemplify: Siemplify connector instance for logging
    
    Returns:
        dict: Filtered domains dictionary
    
    Raises:
        Exception: If no domains match the selected domain names
    """
    siemplify.LOGGER.info(f"Filtering available domains using user input: {selected_domains}")

    # If selected_domains is "All", do not filter
    if not selected_domains or selected_domains.strip().lower() == "all":
        return domains
    
    # Create a list of domain names from the comma-separated string
    domain_names_to_include = [name.strip() for name in selected_domains.split(",")]
    
    # Create a new domains dictionary with only the selected domains
    filtered_domains = {}
    for domain_id, domain_info in domains.items():
        if domain_info.get('name') in domain_names_to_include:
            filtered_domains[domain_id] = domain_info
    
    # Check if domains is empty after filtering and raise an error if it is
    if not filtered_domains:
        error_msg = "No domains matched the selected domain names. Please check your 'Selected Environments' configuration."
        siemplify.LOGGER.error(error_msg)
        raise Exception(error_msg)
    
    return filtered_domains

def filter_finding_types(domains, selected_finding_types, siemplify):
    """
    Filter finding types for each domain based on user selection
    
    Args:
        domains (dict): Dictionary of domains with their available types
        selected_finding_types (str): Comma-separated string of finding types to include
        siemplify: Siemplify connector instance for logging
    
    Returns:
        dict: Domains dictionary with filtered available_types
    
    Raises:
        Exception: If no domain has any matching finding types
    """
    siemplify.LOGGER.info(f"Filtering finding types using user input: {selected_finding_types}")
    # If selected_finding_types is "All", do not filter
    if not selected_finding_types or selected_finding_types.strip().lower() == "all":
        return domains
    
    # Create a list of finding types from the comma-separated string
    finding_types_to_include = [ftype.strip() for ftype in selected_finding_types.split(",")]
    
    # Flag to track if any domain has matching finding types
    any_domain_has_findings = False
    
    # Filter the available_types in each domain
    for domain_id in domains:
        if 'available_types' in domains[domain_id]:
            # Keep only the finding types that are in the selected_finding_types list
            domains[domain_id]['available_types'] = [
                ftype for ftype in domains[domain_id]['available_types'] 
                if ftype in finding_types_to_include
            ]
            
            # Check if available_types is empty after filtering
            if domains[domain_id]['available_types']:
                any_domain_has_findings = True
    
    # If no domain has matching finding types, raise an error
    if not any_domain_has_findings:
        error_msg = "No finding types matched the selected finding types. Please check your 'Selected Finding Types' configuration."
        siemplify.LOGGER.error(error_msg)
        raise Exception(error_msg)
    
    return domains

def update_domain_dates(siemplify, domain_latest_dates):
    """
    Update and store the latest update dates for domains
    
    Args:
        siemplify: Siemplify connector instance
        domain_latest_dates (dict): Dictionary mapping domain names to their latest update dates
    """
    # Get existing dates to merge with new ones
    existing_dates = get_domain_last_created_dates(siemplify)
    
    # Update with the latest dates from this run
    for domain_name, latest_date in domain_latest_dates.items():
        if latest_date:
            existing_dates[domain_name] = latest_date
    
    # Store the updated dates dictionary
    if existing_dates:
        siemplify.LOGGER.info(f'*****updating with data {existing_dates}******')
        store_domain_last_created_dates(siemplify, data=existing_dates)

# Listed below are the sub-functions associated with the main function.
@output_handler
def main(is_test_run):
    """
    Main function that orchestrates the connector workflow
    
    Args:
        is_test_run: Boolean indicating if this is a test run
    """
    # Initialize Siemplify connector
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = ALERT_CONNECTOR_NAME

    # Extract connection parameters
    tenant_domain = siemplify.extract_connector_param(param_name="BloodHound Enterprise Server")
    token_id = siemplify.extract_connector_param(param_name="Token ID")
    token_key = siemplify.extract_connector_param(param_name="Token Key")
    selected_domains = siemplify.extract_connector_param(param_name="Selected BloodHound Environments")
    selected_finding_types = siemplify.extract_connector_param(param_name="Selected Finding Types")
    delete_state = siemplify.extract_connector_param(param_name="delete state")

    if delete_state:
        siemplify.LOGGER.info('***** Clearing the state of the connector ******')
        store_domain_last_created_dates(siemplify, {})

    siemplify.LOGGER.info(f"Connector identifier: {siemplify.context.connector_info.identifier}")
    
    # Check if parameters are missing
    if not token_id or not token_key or not tenant_domain:
        siemplify.LOGGER.error("Missing credentials or domain in configuration.")
        return

    if is_test_run:
        siemplify.LOGGER.info('***** This is a test run ******')
    
    # Initialize BloodHound manager
    bhe_manager = BloodhoundManager(tenant_domain, token_id, token_key, logger=siemplify.LOGGER)

    try:
        # Step 1: Test connection to BloodHound Enterprise
        response = test_bloodhound_connection(bhe_manager, siemplify)
        
        if response:
            # Step 2: Get available domains
            domains = get_available_domains(bhe_manager, siemplify)
            
            # Step 3: Filter domains based on user selection
            domains = filter_domains(domains, selected_domains, siemplify)
            
            # Apply test run limitation for domains
            if is_test_run and domains:
                siemplify.LOGGER.info('Processing only one domain as this is the test run.')
                first_id = next(iter(domains.keys()))
                domains = {first_id: domains[first_id]}
            
            # Step 4: Add available types to each domain in the dictionary
            domains = collect_available_types(bhe_manager, domains,siemplify)
            
            # Step 5: Filter finding types based on user selection
            domains = filter_finding_types(domains, selected_finding_types, siemplify)
            
            # Apply test run limitation for available types
            if is_test_run:
                for domain_id in domains:
                    types = domains[domain_id].get('available_types', [])
                    domains[domain_id]['available_types'] = types[:1] if types else []
            
            # Step 6: Fetch path titles for each unique finding type
            attack_paths_info = fetch_path_info(bhe_manager, domains, siemplify)
            
            # Step 7: Fetch ONLY NEW attack path details for each domain and finding type
            # Only paths with created_at > previously stored created_at are included
            attack_path_details, domain_latest_dates = fetch_attack_path_details(
                bhe_manager, 
                domains, 
                siemplify, 
                tenant_domain, 
                is_test_run
            )
            
            # Step 8: Create alerts from attack path details
            # Only create alerts for attack paths that are newer than last created_at
            alerts = create_alerts(attack_path_details, domains, attack_paths_info, tenant_domain, siemplify)
            
            # Step 9: Store the latest update dates for all domains
            if not is_test_run:
                update_domain_dates(siemplify, domain_latest_dates)
            
            # Step 10: Return alerts to Siemplify
            siemplify.LOGGER.info("------------------- Main - Finished -------------------")
            siemplify.return_package(alerts)
        else:
            # Enhanced error message for authentication failure
            error_msg = "Authentication failed. Please check your 'BloodHound Enterprise Server URL', 'Token ID', and 'Token Key' configurations."
            siemplify.LOGGER.error(error_msg)
            siemplify.LOGGER.error(f"Connection response: {response}")
            raise Exception(error_msg)

    except Exception as error:
        output_message = f"Failed to connect to the {INTEGRATION_NAME} server! Error is {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

if __name__ == "__main__":
    is_test_run = not (len(sys.argv) > 1 and sys.argv[1] == 'True')
    main(is_test_run)