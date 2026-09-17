export interface TestFile {
  file_id: number;
  file_path: string;
}

export interface TestResult {
  status: string;
  message?: string;
  duration_seconds?: number;
  test_files?: string[];
  stdout?: string;
  stderr?: string;
  output?: string;
  return_code?: number;
  generated_test?: boolean;
  generated_test_code?: string;
}

const API_URL = "http://127.0.0.1:8000";

function getToken() {
  return localStorage.getItem("token");
}

async function getErrorMessage(
  response: Response,
  fallback: string
) {
  const data = await response.json().catch(
    () => null
  );

  return data?.detail || fallback;
}

export async function getProjectTests(
  projectId: number
): Promise<TestFile[]> {
  const token = getToken();

  const response = await fetch(
    `${API_URL}/test-runner/project/${projectId}/tests`,
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Failed to load tests"
      )
    );
  }

  const data = await response.json();

  return data.tests || [];
}

export async function runProjectTests(
  projectId: number
): Promise<TestResult> {
  const token = getToken();

  const response = await fetch(
    `${API_URL}/test-runner/project/${projectId}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Failed to run tests"
      )
    );
  }

  return response.json();
}

export async function runSpecificTest(
  projectId: number,
  testPath: string
): Promise<TestResult> {
  const token = getToken();

  const response = await fetch(
    `${API_URL}/test-runner/project/${projectId}?test_path=${encodeURIComponent(
      testPath
    )}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Failed to run test"
      )
    );
  }

  return response.json();
}

export async function runGeneratedTest(
  projectId: number,
  testCode: string,
  testFileName = "generated_ai_test.py"
): Promise<TestResult> {
  const token = getToken();

  const response = await fetch(
    `${API_URL}/test-runner/project/${projectId}/generated`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        test_code: testCode,
        test_file_name: testFileName
      })
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Failed to run generated test"
      )
    );
  }

  return response.json();
}
