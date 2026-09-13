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


export async function getProjectRelationships(
  projectId: number
): Promise<RelationshipsResponse> {

  const response = await fetch(
    `http://127.0.0.1:8000/relationships/project/${projectId}`
  );

  if (!response.ok) {
    throw new Error(
      "Failed to fetch project relationships"
    );
  }

  return response.json();
}