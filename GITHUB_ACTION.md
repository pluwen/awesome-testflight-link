# GitHub Action 工作流说明
The repository contains 3 workflows:
* `Update TestFilght Link Status`: Update the status of the TestFlight link in the repository every day (3:00 UTC every day)
* `Add A TestFilght Link`: Manually add a TestFlight link
* `Del A TestFilght Link`: Manually delete a TestFlight link

## Update repository link description
### 1. Update the status of the link:
You don't need to update the status manually, Github Action will check and update the status automatically every day. Of course, you can manually run the `Update TestFilght Link Status` Github Action Workflow to update the status of links in the repository.

### 2. Add or remove TestFlight public test links
You can run the `Add A TestFilght Link` or `Del A TestFilght Link` Github Action Workflow to add or delete a TestFlight public test link. Just click Actions at the top and select the corresponding Workflow name on the left, then click Run workflow on the right to enter the corresponding parameters as prompted.
There is no setting modification, because it feels unusable, and I am too lazy to do it.

### 3. Add or remove links to non-TestFlight public tests (such as TestFlight tests that require a form application)
Because this part of the link is not intended to be put into the database, if you need to add or delete this type of link, please manually modify the [`./scripts/data/signup.md`](./scripts/data/signup.md) file, Then manually run any workflow once (recommended to run `Update TestFilght Link Status`) to also update your changes in [`./README.md`](./README.md) on the front page.

### 4. Other Instructions
Since this repository contains [binary database file] (./db/sqlite3.db), after others pull the repository and update it, please make sure you synchronize the repository before submitting the PR, and then make changes to avoid conflicts when merging PRs deal with. Try not to modify the database file (including running the workflow will also modify the database file), the warehouse owner is merging __For those who have changed the database file, try to download and check whether the database file changed by the other party is normal before PR__ (to avoid malicious damage or modification of the database file).
