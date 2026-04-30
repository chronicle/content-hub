# Content Hub Parsers

Welcome to the open-source repository for Google SecOps parsers. This initiative aims to foster community contributions to expand and maintain the available set of parsers for Google Security Operations. 

## Goals
* **Enable Community Contributions**: Allow external users, partners, and customers to contribute new and updated "community parsers".
* **Facilitate Adoption**: Provide customers with a mechanism to adopt community parsers into their custom parser instances.
* **Ensure Quality**: Maintain a rigorous vetting and testing framework to guarantee the security and functional quality of all contributions before release.

## Repository Structure

All parsers are organized within the top-level `parsers/` directory in the `content-hub` repository. Each log source has its own dedicated subdirectory.
```
content-hub/
└── content/
    └── parsers/
        ├── third_party/
        │   ├── community/
        │   │   ├── VENDOR1_PRODUCT1/cbn/
        │   │   ├                     ├── <config>.conf
        │   │   ├                     ├── metadata.json
        │   │   ├                     └── testdata/
        │   │   ├                           ├── raw_logs/
        │   │   ├                           │   └── <usecase>_log.json
        │   │   ├                           └── expected_events/
        │   │   ├                               └── <usecase>_events.json
        │   ├── partner/
        │   │   ├── partnerA/
        │   │   │     └── VENDOR1_PRODUCT1/cbn/
        │   │   │                     ├── <config>.conf
        │   │   │                     ├── metadata.json
        │   │   │                     └── testdata/
        │   │   │                           ├── raw_logs/
        │   │   │                           │   └── <usecase>_log.json
        │   │   │                           └── expected_events/
        │   │   │                               └── <usecase>_events.json
        │   │   └── partnerB/
        │   │   │    └── VENDOR1_PRODUCT1/cbn/
        │   │   │                     ├── <config>.conf
        │   │   │                     ├── metadata.json
        │   │   │                     └── testdata/
        │   │   │                           ├── raw_logs/
        │   │   │                           │   └── <usecase>_log.json
        │   │   │                           └── expected_events/
        │   │   │                               └── <usecase>_events.json
        ...
```

## Parser Folder Contents
Each subdirectory under folder `cbn/` will contain the following files:

**`<config>.conf`**: This file contains the core parser logic using the Configuration Based Normalization (CBN) syntax. It defines the filters and mutations necessary to convert raw log data into the Unified Data Model (UDM) structure. Name of the file is flexible, can be any valid name. 

**`metadata.json`**: A JSON file providing essential metadata about the parser. This allows users and potential automation to quickly understand the parser's context and intended use. Naming of the file fixed ahd has to be metadata.json. The structure will be as follows:
```json
{
  "log_type": "AZURE_AD", // (Optional)
  "product": "Azure Product",
  "vendor": "Microsoft",
  "supported_format": "SYSLOG,CSV", // (Optional)
  "category": "Identity and Access Management", // (Optional)
  "description": "Parses audit logs from Azure Product.", // (Optional)
  "references": "" // (Optional)
}
```
* **log_type**: The specific Google Security Operations LogType identifier (e.g., APACHE, GCP_CLOUDAUDIT).
* **product**: Human-readable name of the software or service.
* **vendor**: The vendor of the product.
* **supported_format**: The formats of the log that are supported by the parser.
* **category**: The formats of the log that are supported by the parser.
* **description**: A brief explanation of what the parser does.
* **references**: A public documentation link regarding the log source.

**`testdata/` (Directory)**: This subdirectory houses files for testing the parser's correctness:
* **`*_log.json` or `*.txt` files**: Sample raw log files (e.g., `sample_input_log.json`). These files contain representative log entries that the parser is expected to process. Naming of the file is flexible in the beginning but has to end with _log.json. 
* **`*_events.json` files**: JSON files representing the expected UDM output for each corresponding input log file (e.g., `sample_input_events.json`). The JSON structure must conform to the publicly documented Google Security Operations UDM schema. This allows for validation without exposing internal proto definitions. Naming of the file is flexible but has to end with _events.json and for any log - event pair their prefixes are mandatariliy be same (e.g. `sample_input_log.json` and `sample_input_events.json`)

**`README.md` (Optional)**: Any specific instructions, notes on log formats, common issues, or other documentation relevant to this particular parser.