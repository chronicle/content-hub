# How to Contribute a Playbook

Before contributing, please review the general [contribution guidelines](/docs/contributing.md).

There are two ways to contribute a playbook:

## 1. Using the `mp` tool (Recommended)

The `mp` tool helps automate the process of pulling, validating, and structuring your playbook.

- ### 1.1. Install 'mp'
    - [Follow the installation guide](/packages/mp/docs/installation.md).

- ### 1.2. Pull the playbook from SOAR
    - [Use the
      'dev-env' commands to login and pull the playbook](/packages/mp/docs/commands/dev_env.md).
  ```bash
  mp dev-env login --api-root <soar_url> --api-key <api_key>
  
  mp dev-env pull playbook <playbook_name>
  ```

- ### 1.3. Move the pulled playbook
    - Move the playbook to the correct directory:
        - For community playbooks: `content/playbooks/third_party/community/`
        - For partner playbooks: `content/playbooks/third_party/partner/`

- ### 1.4. Fill the `display_info.yaml` file
    - Provide the required metadata (e.g., display name, author, description).

- ### 1.5. Validate the playbook
    - [Run `mp validate`](/packages/mp/docs/commands/validate.md) to ensure the playbook passes all
      checks.

- ### 1.6. Create a Pull Request
    - Create a Pull Request on the `content-hub` GitHub repository.

- ### 1.7. Await review and approval
    - The Content Hub team will review your submission and may request changes before merging.

## 2. Manual Process

If you prefer to contribute manually, follow these steps:

- ### 2.1. Export the playbook
    - In your Google SecOps instance, navigate to the playbook and export it.
      ![Export Playbook](/docs/resources/playbooks/export_playbook.png)

- ### 2.2. Unzip the playbook
    - The exported file is a zip archive. Unzip it to extract the playbook JSON file.

- ### 2.3. Place the playbook JSON in the repository
    - Move the extracted playbook JSON file to the appropriate directory:
        - Community contributions: `content/playbooks/third_party/community/`
        - Partner contributions: `content/playbooks/third_party/partner/`

- ### 2.4. Deconstruct the playbook
    - At the root of the repository, run the following command:
      ```bash
      mp build -p <playbook_name> --deconstruct
      ```
      Replace `<playbook_name>` with your playbook's name.

- ### 2.5. Move the deconstructed playbook files
    - The previous command creates an `out` folder. Move the deconstructed playbook directory from
      `out/content/playbooks/third_party/...` to the correct location in the main
      `content/playbooks/third_party/` directory, replacing the original JSON file.

- ### 2.6. Fill the `display_info.yaml` file
    - In your new playbook directory, open `display_info.yaml` and provide the required metadata (
      e.g., display name, author, description).

- ### 2.7. Create a Pull Request
    - Commit your changes and push them to your fork.
    - Open a pull request against the main `content-hub` repository.

- ### 2.8. Await review and approval
    - The Content Hub team will review your submission and may request changes before merging.
