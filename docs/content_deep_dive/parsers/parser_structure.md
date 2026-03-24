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
        │   │   └── VENDOR2_PRODUCT2/cbn/
        │   ├── partnerA/
        │   │   └── VENDOR1_PRODUCT1/cbn/
        │   └── partnerB/
        │        └── VENDOR1_PRODUCT1/cbn/
        ...
```

## Parser Folder Contents
Each subdirectory under folder `cbn/` will contain the following files:

**`parser.conf`**: This file contains the core parser logic using the Configuration Based Normalization (CBN) syntax. It defines the filters and mutations necessary to convert raw log data into the Unified Data Model (UDM) structure.

**`metadata.json`**: A JSON file providing essential metadata about the parser. This allows users and potential automation to quickly understand the parser's context and intended use. The structure will be as follows:
```json
{
  "log_type": "AZURE_AD", // (Optional)
  "product": "Azure Product",
  "vendor": "Microsoft",
  "supported_format": "SYSLOG,CSV", // (Optional)
  "category": "Identity and Access Management", // (Optional)
  "description": "Parses audit logs from Azure Product.", // (Optional)
  "references": "", // (Optional)
  "verified": true // (Optional)
}
```
* **log_type**: The specific Google Security Operations LogType identifier (e.g., APACHE, GCP_CLOUDAUDIT).
* **product**: Human-readable name of the software or service.
* **vendor**: The vendor of the product.
* **supported_format**: The formats of the log that are supported by the parser.
* **category**: The formats of the log that are supported by the parser.
* **description**: A brief explanation of what the parser does.
* **references**: A public documentation link regarding the log source.
* **verified**: If true, it means that the parser is validated on the SecOps instance.

**`testdata/` (Directory)**: This subdirectory houses files for testing the parser's correctness:
* **`*.json` or `*.txt` files**: Sample raw log files (e.g., `sample_input.json`). These files contain representative log entries that the parser is expected to process.
* **`*_expected.json` files**: JSON files representing the expected UDM output for each corresponding input log file (e.g., `sample_input_expected.json`). The JSON structure must conform to the publicly documented Google Security Operations UDM schema. This allows for validation without exposing internal proto definitions.

**`README.md` (Optional)**: Any specific instructions, notes on log formats, common issues, or other documentation relevant to this particular parser.