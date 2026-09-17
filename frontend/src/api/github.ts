import { apiFetch } from "./apiFetch";


export interface GitHubChangedFiles {
  added: string[];
  modified: string[];
  deleted: string[];
}


export interface GitHubImportResponse {
  message: string;

  project_id: number;

  repository: string;

  owner: string;

  default_branch: string;

  github_url?: string;

  commit_sha?: string;

  previous_commit_sha?: string;

  files_processed: number;

  chunks_created: number;

  embedding_model: string;

  changed_files?: GitHubChangedFiles;

  reindexed?: boolean;
}


function validateGithubUrl(
  githubUrl: string
): string {

  const url = githubUrl.trim();

  if (!url) {
    throw new Error(
      "Please enter a GitHub repository URL."
    );
  }

  let parsedUrl: URL;

  try {

    parsedUrl = new URL(url);

  } catch {

    throw new Error(
      "Invalid URL. Please enter a valid GitHub repository URL."
    );
  }

  if (
    parsedUrl.protocol !== "https:"
  ) {

    throw new Error(
      "GitHub URL must use HTTPS."
    );
  }

  if (
    parsedUrl.hostname.toLowerCase()
    !== "github.com"
  ) {

    throw new Error(
      "Please enter a URL from github.com."
    );
  }

  const parts =
    parsedUrl.pathname
      .split("/")
      .filter(Boolean);

  if (parts.length < 2) {

    throw new Error(
      "Invalid GitHub repository URL. Use https://github.com/owner/repository."
    );
  }

  if (parts.length > 2) {

    throw new Error(
      "Please enter a repository URL, not a GitHub file, folder, issue, or pull-request URL."
    );
  }

  const owner = parts[0];

  const repository =
    parts[1].replace(
      /\.git$/i,
      ""
    );

  if (
    !owner
    || !repository
  ) {

    throw new Error(
      "Invalid GitHub repository URL. Use https://github.com/owner/repository."
    );
  }

  return (
    `https://github.com/${owner}/${repository}`
  );
}


function getImportErrorMessage(
  status: number,
  detail: unknown
): string {

  if (
    typeof detail === "string"
    && detail.trim()
  ) {

    return detail;
  }

  if (status === 401) {

    return (
      "Authentication failed. Please log in again."
    );
  }

  if (status === 404) {

    return (
      "Project not found or you do not have access to it."
    );
  }

  if (status === 413) {

    return (
      "Repository is too large. Maximum allowed is 200 files and 50 MB uncompressed."
    );
  }

  if (status === 429) {

    return (
      "Too many requests. Please wait and try again."
    );
  }

  if (status >= 500) {

    return (
      "GitHub import failed on the server. Please try again."
    );
  }

  return (
    "Could not import GitHub repository."
  );
}


export async function importGithubRepository(
  projectId: number,
  githubUrl: string
): Promise<GitHubImportResponse> {

  if (
    !Number.isInteger(projectId)
    || projectId <= 0
  ) {

    throw new Error(
      "Please select a valid project first."
    );
  }

  const validatedUrl =
    validateGithubUrl(
      githubUrl
    );

  const response =
    await apiFetch(
      "/github/import",
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body: JSON.stringify({
          project_id: projectId,
          github_url: validatedUrl,
        }),
      }
    );

  const data =
    await response
      .json()
      .catch(
        () => null
      );

  if (!response.ok) {

    throw new Error(
      getImportErrorMessage(
        response.status,
        data?.detail
      )
    );
  }

  return data as GitHubImportResponse;
}


export async function reimportGithubRepository(
  projectId: number
): Promise<GitHubImportResponse> {

  if (
    !Number.isInteger(projectId)
    || projectId <= 0
  ) {

    throw new Error(
      "Please select a valid project first."
    );
  }

  const response =
    await apiFetch(
      `/github/reimport/${projectId}`,
      {
        method: "POST",
      }
    );

  const data =
    await response
      .json()
      .catch(
        () => null
      );

  if (!response.ok) {

    if (
      typeof data?.detail
      === "string"
    ) {

      throw new Error(
        data.detail
      );
    }

    if (response.status === 401) {

      throw new Error(
        "Authentication failed. Please log in again."
      );
    }

    if (response.status === 404) {

      throw new Error(
        "Project not found or you do not have access to it."
      );
    }

    if (response.status === 400) {

      throw new Error(
        data?.detail
        ||
        "This project does not have a saved GitHub repository."
      );
    }

    if (response.status === 413) {

      throw new Error(
        "Repository is too large. Maximum allowed is 200 files and 50 MB uncompressed."
      );
    }

    if (response.status === 429) {

      throw new Error(
        "Too many requests. Please wait and try again."
      );
    }

    throw new Error(
      "Could not refresh GitHub repository."
    );
  }

  return data as GitHubImportResponse;
}