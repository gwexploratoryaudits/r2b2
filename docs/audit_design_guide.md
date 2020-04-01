# Instructions for Designing an Audit

Building an audit into the R2B2 library includes:

- Designing the specific audits object class
- Implementing the methods needed to compute and execute the `Audit`
- Designing tests to verify functionality of your code
- Merging the new audit into the current version of R2B2

## Setting up Development Environment

1. Create a base branch for working on the new audit.
  - Example: If your audit was named Sarah, first create a branch named `sarah` off of master.
  First check what branch you are working on:
```
$ git status
On branch master
...
```
If you are not on `master`, run:
```
$ git checkout master
```
Finally, checkout your branch from `master` and create a remote version of that branch:
```
$ git checkout -b sarah
$ git push -u origin sarah
```
  - Feel free to create branches of of this base branch as you work on developing the audit, but keep in mind that branches should be used for larger changes/additions. For example, creating a branch for fixing documentation and comments probably isn't a good idea, but creating a branch for developing a comprehensive set of test cases could be useful.
  - Note: We will use the base branch for your audit when merging into `master`.

2. Choose an IDE or text editor.
  - If you use an IDE with plugins for linting, ensure it uses `flake8`.
  - If you are running code from within your IDE, ensure it uses to correct versions of Python, libraries, and any other tools used to test code.
  - For more details and information on the style guide, see the design guide document.
3. Ensure all tests are passing on the shiny new branch.
  - From the root directory of the repo, run:
  ```
  tox
  ```
  You should see a message like this:
  ```
  clean: commands succeeded
  check: commands succeeded
  docs: commands succeeded
  py37: commands succeeded
  report: commands succeeded
  ```
  If instead you see something like this:
  ```
  clean: commands succeeded
  ERROR:  check: commands failed
  docs: commands succeeded
  py37: commands succeeded
  report: commands succeeded
  ```
  You can use, `tox -e check` (or insert the test which failed) to investigate why the test might have failed.
  - If you have a failing test and cannot determine what is causing the error, reach out to Sarah or Grant to help fix the problem before you begin working (it is always best to begin from a clean slate).

## Understanding the Workflow

Even though you might be the only person working on your branch right now, your `git` history will eventually be seen by others (and included on `master`), so it is important to use `git` best practices from the beginning.

1. Writing code.
  - Starting from scratch can be difficult. If you are not sure where to start, try starting at a very high level, leaving places where code will eventually go with placeholder `TODO: ` comments, then filling in the skeleton.
  - When you are in the zone and can't be bothered to write comments/documentation:
    - Docstrings are most important for generating documentation and introducing your code to people who are unfamiliar with it. **During development it is OK to leave a docstring as a** `TODO: ` until you are done building the module/class/function.
    - Comments that make sense of complex lines of code are important! **Do not** leave pieces of code that are difficult to understand uncommented in a commit. If you are not sure what warrant complex code, read the rest of the source code to get an idea.
2. Committing (and perhaps stashing) your changes.
  - Commit modular changes. Examples might include:
    - A full implementation of a new function.
    - Updated and complete documentation for a class or module.
    - A new set of test cases (which are hopefully passing).
  - Write useful commits messages. **Do not** use `git commit -m`. Instead, use one of
    ```
    git commit -a   // to stage and commit all tracked files, or
    git commit      // to commit all staged files
    ```
    to commit your changes and open a text editor where you can write you commit message. Commit messages should be a short, one-line summary (no more than 50 characters) followed by a blank line, then a detailed summary of changes:
    ```
    Short one-line summary.

    Longer, detailed explanation of changes.
    This might be multiples lines.
    ```
    *Note:* If you run a `commit` command accidentally and wish to abort, simply do not enter a commit message or force quit from the text editor. In Vim, this would be `:q!`.
  - If you find yourself working on changes that are unrelated to the current changes you want to commit, or changes that might belong on another branch, use `gits stash`. *Note:* `git stash` will only save locally so no need to worry about meeting any development standards when you want to stash something, it is only for you.
    - Run `git stash push -m 'Reminder about what this stash is.'` to save the changes for later.
    - Run `git stash pop` to restore changes you previously saved.
3. Pushing to GitHub
  - Every time you `git push` to GitHub, Travis CI will remotely run all of our test cases. To see if your remote tests are passing, find the most recent build of your branch [here](https://travis-ci.org/github/gwexploratoryaudits/r2b2/branches?utm_medium=notification&utm_source=github_status).
  - If you had all the tests passing locally using `tox`, they should all pass here. If they do not, check the error messages on Travis:
    - Sometimes server timeout can incorrectly cause tests to fail. If you believe this to be the case, restart the build on Travis before making changes.
    - Ensure that when `tox` runs locally it is using all the correct versions (i.e. the same versions as Travis), if there is a mismatch, update you system to use the version used by Travis. If you do not want to uninstall or reinstall anything, try using Pythons [virtual environments](https://docs.python.org/3/tutorial/venv.html) when you work on the repo.

## Building the Audit

1. Create the new audit class as a subclass of the abstract `Audit` class.
2. Implement the required methods:
  - `__init__()`
  - `stopping_condition()`
  - `next_sample_size()`
  - `stopping_condition()`
  - `next_min_winner_ballots()`
  - `compute_min_winner_ballots()`
  - `compute_risk()`
3. Implement any additional audit specific methods.
4. Add docstrings (using the Google style) to modules, classes, and methods.
  - If you want to see if your docstrings are being generated correctly in the documentation, run `tox -e docs`, then open your local copy of the documentation from `r2b2/dist/docs/index.html` in a browser.
5. Write test cases for your audits.
  - Create unit tests to verify the basic functionality of methods and ensure proper initialization occurs.
  - Create a set of tests to verify mathematical validity of the audit computations
    - *Note:* Test data sets will be created, so don't worry about these tests just yet.
6. Debug! Ensure your test cases (and all other test cases that were previously passing) are passing.

## Merging into `master`

1. Open a Pull Request.
  - Collaborating is a big part of this library, so feel free to open a PR on a branch that is not yet complete. **If you want to open a PR before a branch can be merged, simply put `WIP: ` before the title.`**
2. Get ready to merge.
  - [ ] *If applicable*: Remove `WIP: ` from title and indicate that the branch is ready to merge.
  - [ ] Request a review from Sarah and/or Grant and get it approved.
  - [ ] *If applicable*: Make changes per review or code review on group call.
  - [ ] Ensure all Travis and Codecov tests pass (GitHub will show this at the bottom of the PR).
  - [ ] Ensure there are no merge conflicts with the branch you are attempting to merge into. If there are conflicts, resolve them before merging.
3. Merge your branch!
  - On GitHub, rebase and merge (this should be the default option in the PR).
