# TIPCommon

TIPCommon is a package that contains code that can be shared to all integrations when using it as a dependency.
The package consists of different modules for different types of usages, for example, IO, time based logic, parameter validation, filtering etc.

---

## Contribution

### Key Points

Contributions to the marketplace’s common code are very encouraged!
Changes like adding common function and logic, fixing or improving common code, adding capabilities to base-classes etc…

When making changes to common code make sure to keep in mind few things:

- This code will affect every integration that might use it! If an introduced change is regressive to previous versions, it must be tagged as one in the RN
- The changes should be as general as possible, and have to abide the Google Python Style Guide <https://google.github.io/styleguide/pyguide.html>
- The change must be written as clearly as possible

### Steps for Contribution

#### (1) Create The Changes in Local Repo

The code changes should be as generic as possible, so they can be used in every integration.

#### (2) Create the Dependency and Update the Relative Packages

In your CL branch, run the `/Common/Scripts/UpdateCommonDependenciesScript` (please see the script's `README.md`) with the new version to create your new desired dependency.  
Most of the times the version should be an increase to the minor part (i.e. the leftmost number) of the previous version (1.1.9 → 1.1.10).  
Run the script to create your desired dependency (TIPCommon or EnvironmentCommon) and the script will create and update the correct packages in the `/Common/Packages` directory. If you specify an integration then it will also update the integration itself, although this functionality is mainly used for testing - in your common-code CL try to avoid changes that are not in the common code!

#### (3) Release Notes

If the change was in TIPCommon, just like we do for integrations, add release notes in `/Common/SourceCode/TIP/ReleaseNotes/RN.json`.
Don’t forget to specify the correct change tags (new, regressive, deprecated…) and add one RN object for each change. Look at some previous release notes for context if you're not familiar with the marketplace's RN format.

#### (4) Create a new CL

The CL commit message should be according to the Google Code Review Devguide (go/cl-descriptions), and contain the following in the message body:

```log
What: Describe what was changed in a single line
Where: Describe which modules were changed
Why: What is the reason for the change
```

The newly created CL should contain only common-code!   
A CL with changes both to common code and other changes will not be merged!

* NOTE: Use a relation chain if you need the changes for completing another task.

#### Reviews and Release

Finally you can test your code and pass it through the usual release process, QA and finally,  MarketPlace Infra developer code review before the release.
