# How to Contribute an Integration

Before contributing, please review the general [contribution guidelines](/docs/contributing.md).

There are two ways to contribute an integration:

## 1. Using the `mp` tool (Recommended)

The `mp` tool helps automate the process of pulling, validating, and structuring your integration.

- ### 1.1. Install 'mp'
    - [Follow the installation guide](/packages/mp/docs/installation.md).

- ### 1.2. Pull the integration from SOAR
    - [Use the
      'dev-env' commands to login and pull the integration](/packages/mp/docs/commands/dev_env.md).
  ```bash
  mp dev-env login --api-root <soar_url> --api-key <api_key>
  
  mp dev-env pull integration <integration_name> [option] --dest <pull_destionation_folder>
  ```

- ### 1.3 Fill the `release_notes.yaml` file

- ### 1.5. Move the pulled integration
    - Move the integration to the correct directory:
        - For community integrations: `content/response_integration/third_party/community/`
        - For partner integrations: `content/response_integration/third_party/partner/`

- ### 1.6. Validate the integration
    - [Run
      `mp validate`](/packages/mp/docs/commands/validate.md) to ensure the integration passes all
      checks.

- ### 1.7. Create a Pull Request
    - Create a Pull Request on the `content-hub` GitHub repository.

- ### 1.8. Await review and approval
    - The Content Hub team will review your submission and may request changes before merging.

## 2. Manual Process

If you prefer to contribute manually, follow these steps:

- ### 2.1. Export the integration
    - In your Google SecOps instance, navigate to the integration and export it.

- ### 2.2. Deconstruct the integration
    - At the root of the repository, run the following command:
      ```bash
      mp build -i <integration_name> --deconstruct --src <path to exported integration>
      ```
      Replace `<integration_name>` with your integration's name.

- ### 2.3. Fill the `release_notes.yaml` file

- ### 2.4. Move the deconstructed integration
    - Move the integration to the correct directory:
        - For community integrations: `content/response_integration/third_party/community/`
        - For partner integrations: `content/response_integration/third_party/partner/`

- ### 2.5. Validate the integration
    - [Run
      `mp validate`](/packages/mp/docs/commands/validate.md) to ensure the integration passes all checks.

- ### 2.6. Create a Pull Request
    - Commit your changes and push them to your fork.
    - Open a pull request against the main `content-hub` repository.

- ### 2.7. Await review and approval
    - The Content Hub team will review your submission and may request changes before merging.
