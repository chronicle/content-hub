# How to Contribute a Playbook

Here are the steps to contribute a new playbook to the Content Hub repository:

1. **Export the playbook from your Google SecOps platform.**
    - Navigate to the playbook in your Google SecOps instance and export it.

   ![playbooks](/docs/resources/playbooks/export_playbook.png)

2. **Unzip the playbook.**
    - The exported file will be a zip file containing the playbook JSON. Unzip it to get the JSON
      file.

3. **Place the playbook JSON in the repository.**
    - Move the extracted playbook JSON file into the appropriate directory:
        - For community contributions: `content/playbooks/third_party/community/`
        - For partner contributions: `content/playbooks/third_party/partner/`

4. **Deconstruct the playbook using the `mp` tool.**
    - Open your command line at the root of the repository and run the following command:
      ```bash
      mp build -p <playbook_name> --deconstruct
      ```
      Replace `<playbook_name>` with the name of your playbook.

5. **Move the deconstructed playbook files.**
    - After the command runs, an `out` folder will be created. Navigate into the `out` folder and
      move the deconstructed playbook directory from `out/content/playbooks/third_party/...` to the
      correct location in the main `content/playbooks/third_party/` directory, replacing the
      original JSON file.

6. **Fill out the `display_info.yaml` file.**
    - Open the `display_info.yaml` file within your new playbook directory and fill in the required
      metadata, such as the display name, author, and a brief description.

7. **Open a Pull Request (PR) on GitHub.**
    - Commit your changes and push them to your forked repository.
    - Open a pull request against the main Content Hub repository.

8. **Wait for review and approval.**
    - The Content Hub team will review your contribution. They may request changes or provide
      feedback before merging your playbook.
