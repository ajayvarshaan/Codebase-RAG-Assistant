export interface Relationship {
  id: number;
  source_file_id: number;
  source_file: string;
  target_file_id: number;
  target_file: string;
  relationship_type: string;
}

export interface RelationshipsResponse {
  project_id: number;
  relationships: Relationship[];
}

const API_URL = "http://127.0.0.1:8000";

function getToken(): string | null {
  return localStorage.getItem("token");
}

export async function getProjectRelationships(
  projectId: number
): Promise<RelationshipsResponse> {

  const token = getToken();

  if (!token) {
    throw new Error(
      "Authentication required. Please log in again."
    );
  }

  const response = await fetch(
    `${API_URL}/relationships/project/${projectId}`,
    {
      method: "GET",

      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {

    const errorData =
      await response
        .json()
        .catch(() => null);

    throw new Error(
      errorData?.detail ||
      "Failed to fetch project relationships"
    );
  }

  return response.json();
}