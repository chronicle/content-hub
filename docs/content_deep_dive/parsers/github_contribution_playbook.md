# **GitHub Contribution Playbook**

# 

| \#begin-approvals-addon-section Username Role Status Last change [idanpatelsky](http://teams/idanpatelsky) Approver 🟢 Approved Jul 30, 2026 [teakay](http://teams/teakay) Approver 🟡 Pending Jul 30, 2026      ![][image1] Approval Instructions: Please approve or LGTM through the [G3 Assist](https://goto.google.com/g3a-approvals-reviewing) sidebar. For more information, see [go/g3a-approvals-reviewing](https://goto.google.com/g3a-approvals-reviewing)  |
| ----- |

# 

# **1.0 Introduction**

This runbook serves as a comprehensive guide for developers and contributors to standardize the process of submitting code to the GitHub repository. By following these procedures, contributors ensure that all additions meet the required quality, security, and functional standards for seamless integration.

# **2.0 Getting Started & Environment Setup**

## **2.1 Folder Structure**

The repository is organized into two primary categories:

* **Community Folder:** For general log type contributions and shared parser logic.  
* **Partner Folder:** Dedicated space for specific vendor or partner-led integrations.

## **2.2 Setup Requirements**

* **Environment Setup:** Ensure your local development environment is configured with the necessary GitHub credentials and dependencies for your specific log types.

#  **GitHub Account & Profile Setup**

**1.1 GitHub Sign In**

* **Access:** [github.com/login](https://github.com/login)

**1.2 Organization Email Setup**

* **Settings:** Profiles → Settings → Emails → Add/Verify Organization email.  
* **Primary:** Set your organization email as primary.  
* **Git Config:**  
* 

```shell
git config --global user.email "your_name@example.com"
```

**1.3 Contributor License Agreement (CLA)**

* **POC:** Google engineering team  
* **Portal:** [cla.developers.google.com](https://cla.developers.google.com/)

**1.4 SSH Key Setup**

* **Generation:**  
* 

```shell
ssh-keygen -t ed25519 -C "your_email@google.com"
```

* **Configuration:** Profiles → Settings → SSH and GPG keys → New SSH key.  
* **Ref:** [Connecting to GitHub with SSH](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)

**1.5 Google Github Space**

* [opensource.corp.google.com/github](https://opensource.corp.google.com/github)

**1.6 Access & Compliance:** Before pushing code, verify that your email ID is registered with the Contributor License Agreement (CLA) or the relevant Google Group to grant the required permissions.

# **3.0 Pull Request Workflow**

* To initiate a formal code review, contributors **must** ensure the feature branch is synchronized with the master branch and provide sufficient context for reviewers.  
* **Branch Management & Push:** Push your completed feature branch to the remote repository. Ensure your commit history is clean—squash related commits if necessary to maintain a clear audit trail before initiating the merge request.  
* **PR Submission & Description:** When opening a Pull Request (PR), you **must** populate the description template thoroughly. It must include:  
  * **Buganizer Reference:** A direct link to the associated tracking ticket.  
  * **Log Samples:** Provide raw input logs alongside the corresponding parsed output to demonstrate correct mapping.  
  * **Test Evidence:** A summary of test execution results or screenshots of your local validation.

### **3.1 Example Description Template**

**Summary:** Add community parser for \<LOG\_TYPE\> log type

- Parses \<LOG\_TYPE\> logs into UDM format.  
- Maps internal status codes to standard severity levels (e.g., CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL).  
- Maps internal state flags to security actions (e.g., new, accepted, resolved, remediation, remediated).  
- Extracts principal, target, cloud, and additional fields from event data.  
* **Standardized Naming:** The PR title **must strictly** follow the format \[b/\<Buganizer\_Ticket\_ID\>\] Feat: \<Title\> to enable automated tracking.  
  \<Ticket can’t be created by the end user. We need to create the ticket.\>PR by CBN team can follow this. 


  
Create a DL in github, tag that group.To-do

# **4.0 Automated Validation Pipeline**

All PRs undergo a series of automated checks through GitHub Workflows: 

Once a pull request is created, verify all automated checks and ensure any failures are promptly resolved.

| Category | Workflow | Purpose |
| :---- | :---- | :---- |
| Standard Workflow | Require Checklist | Enforces completion of PR checklist items. |
|  | Validate Content-Hub | Validates content structure and format. |
|  | Build Content-Hub | Builds the project. |
|  | Lint Content-Hub | Runs linting checks. |
|  | Test Content-Hub | Executes the test suite. |
|  | Test Coverage Gate | Validates minimum coverage thresholds. |
|  | Windows Workflows | Runs Windows-specific tests. |
| Security & Quality | CodeQL Advanced | Analyzes code for vulnerabilities. |
|  | Google Integration Checks | Validates Google-specific integration code. |
|  | GitHub Actions Scan | Scans configurations for security issues. |
|  | Mock Enforcement | Ensures proper use of mocks in tests. |
| Reporting | Comment Validations | Posts validation results as PR comments. |
|  | Comment Tests Report | Posts test results as PR comments. |

# **5.0 Technical Contribution Standards (CBN Guidelines)**

The CBN team performs a rigorous verification of all submissions to ensure production-level stability. After your initial PR submission, the reviewer will replicate your configuration in the internal Cider development environment. This process includes executing the code against your provided log samples to validate that the resulting textproto output conforms to the required data schema.

[CBN Style Guide](https://docs.cloud.google.com/chronicle/docs/reference/parser-syntax)

During this phase, the reviewer audits the submission for:

* **Functional Accuracy:** Consistency between input logs and output formatting.  
* **Technical Standards:** Adherence to the Core Logic, Error Handling, and Data Mapping guidelines outlined in this document.

Once the review is complete, the CBN team will approve the CL or provide feedback. You **must** address all comments and push requested changes to the same branch for re-review.

# **6.0 Review & Merging Lifecycle**

The review process is a collaborative, iterative loop designed to ensure code quality and adherence to security standards.

1. **Phase 1: Assignment & Tracking:** Upon PR submission, a Buganizer ticket is linked to the PR as the single source of truth.  
2. **Phase 2: Technical Review Loop:** An iterative cycle involving reviewer feedback and contributor responses.  
   * **Reviewer Feedback:** Reviewers utilize GitHub’s pull request review interface to leave line-level comments, suggesting code improvements, security hardening, or logic corrections.  
   * **Contributor Response:** You are expected to engage with every thread. Address feedback by:  
     * Applying the necessary code changes and pushing incremental commits to the same PR branch.  
     * Replying to the reviewer’s comment thread confirming the fix, providing context, or requesting clarification.  
   * **Thread Resolution:** A discussion thread is considered 'resolved' only after you have implemented the fix and the reviewer has acknowledged the correction. Avoid resolving threads yourself until the reviewer has verified the change.  
3. **Phase 3: Final Approval & Merging:** Final LGTM is granted once all checks pass and threads are resolved.  
   * Once all threads are marked as resolved and the Automated Validation Pipeline (Section 4\) passes all checks, the assigned reviewer will grant final approval (LGTM).

Upon approval, the PR is merged into the master branch. The associated Buganizer ticket is then automatically updated and transitioned to 'Closed' status.
