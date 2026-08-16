# Gmail notification setup

The weekly publication workflow can send newly discovered publication candidates to Gmail before the website is updated.

## Create a Gmail App Password

1. Turn on 2-Step Verification for the Gmail account that will send the messages.
2. Create a Gmail App Password for this workflow, for example named `GitHub Actions`.
3. Copy the generated 16-character app password.

The normal Gmail account password must not be used.

## Add GitHub Actions secrets

In the repository, open **Settings → Secrets and variables → Actions → New repository secret** and add:

- `GMAIL_USERNAME`: the Gmail address used to send the email.
- `GMAIL_APP_PASSWORD`: the 16-character Gmail App Password.

The current workflow sends the review message to `wangyanshang98@gmail.com`. The recipient can be changed in `.github/workflows/update_publications.yml`.

## Review flow

The workflow runs weekly on Monday at 03:17 UTC (11:17 Beijing time), and can also be started manually from the **Actions** tab.

When new candidates are found:

1. A draft Pull Request is created.
2. An email lists the title, authors, journal, year, DOI link, and Pull Request link.
3. Review the candidates and mark the Pull Request ready for review.
4. Merge the Pull Request only after confirming that the papers are yours.
5. GitHub Pages then publishes the updated list.

If Gmail secrets are not configured, the publication Pull Request is still created and the workflow shows a warning instead of sending an email.
