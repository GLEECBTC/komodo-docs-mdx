## 1. Get to know the project

- Read the [README](/README.md)
- Read the [Code of Conduct](CODE_OF_CONDUCT.md)
- Read the [Contribution guide](CONTRIBUTION_GUIDE.md) (this file)
- Read the [Style guide](STYLE_GUIDE.md)

## 2. Find an issue to work on

- Check the issues, assigned to you on this page: https://github.com/issues/assigned
- Pay attention to the priority labels. Here's a brief description of each of these priority labels:

| Label | Description                                                                                                                                                                                                                                                                                            |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| P0    | These are critical issues that require immediate attention and action. They can be show-stoppers, affecting the overall functionality of the project, or security vulnerabilities that could compromise the system. These issues are the highest priority and should be addressed as soon as possible. |
| P1    | These are important issues that need to be addressed quickly. They could be bugs that significantly affect the user experience or performance issues that could impact the overall functionality of the project. These issues require urgent attention but are not as critical as P0 issues.           |
| P2    | These are issues that are important but not critical. They could be bugs or feature requests that do not impact the overall functionality of the project significantly. These issues need to be addressed but can be prioritized behind P0 and P1 issues.                                              |
| P3    | These are minor issues that do not have a significant impact on the functionality of the project. These could be minor bugs or feature requests that can be addressed later in the development cycle. P3 issues can be deprioritized behind P0, P1, and P2 issues.                                     |

Using these priority labels in GitHub Issues can help our prioritize and manage their work more effectively, ensuring that critical issues are addressed first, and minor issues are addressed as time permits.

## 3. Create a new branch

- Create a new local branch from the `dev` branch (`main` for hotfixes), name it according to [branch naming conventions](GITFLOW_BRANCHING.md#branch-naming-conventions)

## 4. Work on the issue

- Read the issue description and comments
- Make sure that you understand the issue, requirements, security details, etc.
- Move related issue to the "In progress" column on the project board
- Be sure to follow the project's coding style and best practices
- Add your info to the [Authors info file](authors.json). Just the following is enough. Rest of the info is filled in automatically

```json
"<your username>": {
    "username": "<your username>",
        "commit_emails": [<your emails, seperated by commas>],
        "socials": {
            "twitter": "<your twitter username>",
            "linkedin": "your linkedin profile url"
        }
}
```

- Commit your changes in small, logical units with [clear and descriptive commit messages](https://cbea.ms/git-commit/)
- Upload your work branch to the remote, even if it's not finished yet. Update it with new commits as you work on the issue

## 5. Before creating or updating a PR (checklist)

- [ ] Sync your work branch with the latest changes from the target branch (`dev` or `main`), resolve merge conflicts if any
- [ ] (Re)read original issue and comments, make sure that changes are solving the issue or adding the feature
- [ ] Consider adding integration tests for your changes (if applicable)
- [ ] Test your changes manually in different browsers: Chrome, Firefox, Safari, Edge, Brave
- [ ] Add each new page to the [sidebar file](https://github.com/KomodoPlatform/komodo-docs-mdx/blob/main/src/data/sidebar.json)

## 6. Create a PR (checklist)

- [ ] Sync your work branch with the latest changes from the target branch (again :), push it to the remote
- [ ] Make sure that you're opening a PR from your work branch to the proper target branch (`dev` or `main`)
- [ ] Provide a clear and concise title for your PR
  - [ ] Avoid using generic titles like "Fix" or "Update"
  - [ ] Avoid using the issue number in the title
  - [ ] Use the imperative mood in the title (e.g. "Fix bug" and not "Fixed bug")
- [ ] Describe the changes you've made and how they address the issue or feature request
  - [ ] Reference any related issues using the appropriate keywords (e.g., "Closes #123" or "Fixes #456")
  - [ ] Provide test instructions to help QA engineers test your changes (if applicable)
- [ ] Request a code review from one or more maintainers or other contributors
- [ ] Move related issue to the "Review" column on the project board
- [ ] After code review is done, request testing from QA team
- [ ] Move related issue to the "Testing" column on the project board
- [ ] When QA team approves the changes, merge the PR, move related issue to the "Done" column on the project board

## 7. Maintain your PR

- Once your PR is created, you should maintain it until it's merged
- Check the PR on daily basis for comments, changes requests, questions, etc.
- Address any comments or questions from the code review, or from QA testing
- Make sure that your PR is up to date with the target branch (`dev` or `main`), resolve merge conflicts proactively
- After merging, delete your work branch

## 8. 🎉 Celebrate!

- Congratulations! You've just contributed to the project!
- Thank you for your time and effort!
