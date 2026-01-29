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
  
  mp dev-env pull playbook <playbook_name> [option] --dest <pull_destionation_folder>
  ```
- ### 1.3. Fill the `display_info.yaml` file
    - Provide the required metadata (e.g., display name, author, description).

- ### 1.4 Fill the `release_notes.yaml` file

### Note: If your playbook uses blocks that already exist in the "content-hub" repository, you don't need to include them in your pull request. Instead, you should reference the existing blocks. For detailed instructions, see the section on [How to Sync a Playbook with Existing Blocks in the Repo](#how-to-sync-a-playbook-with-existing-blocks-in-the-repo).

- ### 1.5. Move the pulled playbook
    - Move the playbook to the correct directory:
        - For community playbooks: `content/playbooks/third_party/community/`
        - For partner playbooks: `content/playbooks/third_party/partner/`

- ### 1.6. Validate the playbook
    - [Run `mp validate`](/packages/mp/docs/commands/validate.md) to ensure the playbook passes all
      checks.

- ### 1.7. Create a Pull Request
    - Create a Pull Request on the `content-hub` GitHub repository.

- ### 1.8. Await review and approval
    - The Content Hub team will review your submission and may request changes before merging.

## 2. Manual Process

If you prefer to contribute manually, follow these steps:

- ### 2.1. Export the playbook
    - In your Google SecOps instance, navigate to the playbook and export it.

  ![Export Playbook](/docs/resources/playbooks/export_playbook.png)

- ### 2.2. Unzip the playbook
    - The exported file is a zip archive. Unzip it to extract the playbook JSON file.

- ### 2.3. Deconstruct the playbook
    - At the root of the repository, run the following command:
      ```bash
      mp build -p <playbook_name> --deconstruct --src <path to exported playbook>
      ```
      Replace `<playbook_name>` with your playbook's name.

- ### 2.4. Fill the `display_info.yaml` file
    - In your new playbook directory, open `display_info.yaml` and provide the required metadata (
      e.g., display name, author, description).

- ### 2.5. Fill the `release_notes.yaml` file

### Note: If your playbook uses blocks that already exist in the "content-hub" repository, you don't need to include them in your pull request. Instead, you should reference the existing blocks. For detailed instructions, see the section on [How to Sync a Playbook with Existing Blocks in the Repo](#how-to-sync-a-playbook-with-existing-blocks-in-the-repo).

- ### 2.6. Place the non-built playbook in the repository
    - Move the deconstructed playbook to the appropriate directory:
        - Community contributions: `content/playbooks/third_party/community/`
        - Partner contributions: `content/playbooks/third_party/partner/`

- ### 2.7. Create a Pull Request
    - Commit your changes and push them to your fork.
    - Open a pull request against the main `content-hub` repository.

- ### 2.8. Await review and approval
    - The Content Hub team will review your submission and may request changes before merging.

## How to Sync a Playbook with Existing Blocks in the Repo

To sync your playbook with blocks that are already in the repository, follow these steps:

1. **Identify Existing Blocks**: Determine which blocks used by your playbook are already present in
   the `content-hub` repository.

2. **Locate the Block**: Navigate to `content-hub/content/playbooks/` and find the directory for the
   block you want to use.

3. **Copy the Block Identifier**: Open the `<block_name>/definition.yaml` file and copy the
   `identifier` value (the first field in the file).

4. **Update the Playbook Step**:
    * Go to the directory of the playbook you are contributing.
    * Navigate to the `steps` subdirectory and find the step that uses the block (it usually has the
      same name as the block).

5. **Update the `NestedWorkflowIdentifier`**:
    * In the step's configuration file, find the `parameters` section.
    * Locate the parameter named `NestedWorkflowIdentifier` and replace its `value` with the block
      identifier you copied in the previous step.

6. **Repeat for All Blocks**: Repeat this process for all blocks that already exist in the
   repository.
