import re

import httpx


GITHUB_API = "https://api.github.com"


def parse_github_url(url: str):
    value = url.strip()

    if not value:
        raise ValueError(
            "Please enter a GitHub repository URL."
        )

    pattern = (
        r"^https://github\.com/"
        r"([^/]+)/"
        r"([^/#?]+?)"
        r"(?:\.git)?/?$"
    )

    match = re.match(
        pattern,
        value,
        re.IGNORECASE
    )

    if not match:
        raise ValueError(
            "Invalid GitHub repository URL. "
            "Use https://github.com/owner/repository."
        )

    owner = match.group(1).strip()
    repo = match.group(2).strip()

    if not owner or not repo:
        raise ValueError(
            "Invalid GitHub repository URL. "
            "Use https://github.com/owner/repository."
        )

    return owner, repo


async def download_github_repository(url: str):
    owner, repo = parse_github_url(url)

    api_url = (
        f"{GITHUB_API}/repos/"
        f"{owner}/{repo}"
    )

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=60.0
        ) as client:

            # -------------------------------------------------
            # Get repository information
            # -------------------------------------------------

            response = await client.get(
                api_url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )

            if response.status_code == 404:
                raise ValueError(
                    "GitHub repository not found. "
                    "Check the owner, repository name, "
                    "or make sure the repository is public."
                )

            if response.status_code == 403:
                raise ValueError(
                    "GitHub rejected the request. "
                    "The repository may be private, "
                    "or GitHub rate limiting may have been reached."
                )

            response.raise_for_status()

            repository = response.json()

            if repository.get("private"):
                raise ValueError(
                    "Private GitHub repositories are not supported yet. "
                    "Please use a public repository."
                )

            default_branch = repository.get(
                "default_branch"
            )

            if not default_branch:
                raise ValueError(
                    "Could not determine the repository "
                    "default branch."
                )

            # -------------------------------------------------
            # Get latest commit SHA
            # -------------------------------------------------

            branch_url = (
                f"{GITHUB_API}/repos/"
                f"{owner}/{repo}/branches/"
                f"{default_branch}"
            )

            branch_response = await client.get(
                branch_url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )

            if branch_response.status_code == 404:
                raise ValueError(
                    "Could not determine the latest "
                    "GitHub commit."
                )

            if branch_response.status_code == 403:
                raise ValueError(
                    "GitHub rejected the request while "
                    "checking the latest commit."
                )

            branch_response.raise_for_status()

            branch_data = branch_response.json()

            commit = branch_data.get("commit", {})
            commit_sha = commit.get("sha")

            if not commit_sha:
                raise ValueError(
                    "Could not determine the latest "
                    "GitHub commit SHA."
                )

            # -------------------------------------------------
            # Download repository ZIP
            # -------------------------------------------------

            zip_url = (
                f"{GITHUB_API}/repos/"
                f"{owner}/{repo}"
                f"/zipball/{default_branch}"
            )

            zip_response = await client.get(
                zip_url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )

            if zip_response.status_code == 404:
                raise ValueError(
                    "Could not download the GitHub "
                    "repository archive."
                )

            if zip_response.status_code == 403:
                raise ValueError(
                    "GitHub rejected the repository download. "
                    "Please try again later."
                )

            zip_response.raise_for_status()

            return {
                "owner": owner,
                "repo": repo,
                "default_branch": default_branch,
                "commit_sha": commit_sha,
                "zip_data": zip_response.content,
            }

    except httpx.TimeoutException:
        raise ValueError(
            "GitHub request timed out. Please try again."
        )

    except httpx.HTTPStatusError as error:
        raise ValueError(
            "GitHub request failed with status "
            f"{error.response.status_code}."
        )

    except httpx.RequestError:
        raise ValueError(
            "Could not connect to GitHub. "
            "Please check your internet connection "
            "and try again."
        )