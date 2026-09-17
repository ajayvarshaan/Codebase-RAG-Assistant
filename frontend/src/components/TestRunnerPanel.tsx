import { useEffect, useState } from "react";

import {
  getProjectTests,
  runGeneratedTest,
  runProjectTests,
  runSpecificTest
} from "../services/testRunner";

import type {
  TestFile,
  TestResult
} from "../services/testRunner";

import "./TestRunnerPanel.css";

interface TestRunnerPanelProps {
  projectId: number | null;
  generatedTestCode?: string;
  generatedTestFileName?: string;
}

function extractPythonCode(
  value: string
): string {
  const match = value.match(
    /```(?:python|py)?\s*\n?([\s\S]*?)```/i
  );

  if (match?.[1]?.trim()) {
    return match[1].trim();
  }

  return value.trim();
}

export default function TestRunnerPanel({
  projectId,
  generatedTestCode = "",
  generatedTestFileName = "generated_ai_test.py"
}: TestRunnerPanelProps) {
  const [tests, setTests] = useState<TestFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [runningPath, setRunningPath] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] =
    useState<TestResult | null>(null);

  const hasGeneratedTest =
    Boolean(
      generatedTestCode &&
      generatedTestCode.trim()
    );

  async function loadTests() {
    if (projectId === null) {
      setTests([]);
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const data = await getProjectTests(
        projectId
      );

      setTests(data);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not load tests."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTests();
    setResult(null);
  }, [projectId]);

  async function handleRunAll() {
    if (projectId === null) {
      return;
    }

    setRunningPath("all");
    setMessage("");
    setResult(null);

    try {
      const data = await runProjectTests(
        projectId
      );

      setResult(data);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not run tests."
      );
    } finally {
      setRunningPath("");
    }
  }

  async function handleRunTest(
    testPath: string
  ) {
    if (projectId === null) {
      return;
    }

    setRunningPath(testPath);
    setMessage("");
    setResult(null);

    try {
      const data = await runSpecificTest(
        projectId,
        testPath
      );

      setResult(data);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not run test."
      );
    } finally {
      setRunningPath("");
    }
  }

  async function handleRunGeneratedTest() {
    if (
      projectId === null ||
      !generatedTestCode.trim()
    ) {
      return;
    }

    const pythonCode =
      extractPythonCode(
        generatedTestCode
      );

    if (!pythonCode) {
      setMessage(
        "No Python code was found in the generated test."
      );
      return;
    }

    setRunningPath("generated");
    setMessage("");
    setResult(null);

    try {
      const data =
        await runGeneratedTest(
          projectId,
          pythonCode,
          generatedTestFileName
        );

      setResult(data);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not run generated test."
      );
    } finally {
      setRunningPath("");
    }
  }

  return (
    <div className="test-runner-panel">
      <div className="test-runner-header">
        <div>
          <h2>🧪 Automated Test Runner</h2>

          <p>
            Run the project's Python tests directly.
          </p>
        </div>

        <div className="test-runner-actions">
          <button
            type="button"
            className="test-runner-button"
            onClick={handleRunAll}
            disabled={
              projectId === null ||
              runningPath !== ""
            }
          >
            ▶ Run All Tests
          </button>

          <button
            type="button"
            className="test-runner-button"
            onClick={loadTests}
            disabled={
              projectId === null ||
              loading ||
              runningPath !== ""
            }
          >
            ↻ Refresh Tests
          </button>
        </div>
      </div>

      {hasGeneratedTest && (
        <div className="generated-test-runner">
          <div>
            <strong>
              🤖 AI Generated Test Available
            </strong>

            <p>
              Run the generated test against the
              selected indexed project without saving
              it to the project.
            </p>
          </div>

          <button
            type="button"
            className="test-runner-button"
            onClick={handleRunGeneratedTest}
            disabled={
              projectId === null ||
              runningPath !== ""
            }
          >
            {runningPath === "generated"
              ? "Running..."
              : "▶ Run Generated Test"}
          </button>
        </div>
      )}

      {message && (
        <div className="test-runner-message">
          {message}
        </div>
      )}

      <div className="test-runner-tests">
        <h3>Available Tests</h3>

        {loading && (
          <div className="test-runner-empty">
            Loading tests...
          </div>
        )}

        {!loading &&
          tests.length === 0 && (
            <div className="test-runner-empty">
              No Python test files found.
            </div>
          )}

        {!loading &&
          tests.map((test) => (
            <div
              className="test-runner-test"
              key={test.file_id}
            >
              <span className="test-runner-test-name">
                {test.file_path}
              </span>

              <button
                type="button"
                className="test-runner-button"
                onClick={() =>
                  handleRunTest(
                    test.file_path
                  )
                }
                disabled={
                  runningPath !== ""
                }
              >
                {runningPath ===
                test.file_path
                  ? "Running..."
                  : "Run"}
              </button>
            </div>
          ))}
      </div>

      {result && (
        <div className="test-runner-result">
          <h3>
            {result.status === "passed"
              ? "✅ Tests Passed"
              : result.status === "failed"
              ? "❌ Tests Failed"
              : result.status === "timeout"
              ? "⏱️ Tests Timed Out"
              : "ℹ️ No Tests"}
          </h3>

          <p>
            {result.message}
          </p>

          {result.duration_seconds !==
            undefined && (
            <p>
              Duration:{" "}
              {result.duration_seconds}s
            </p>
          )}

          {result.test_files &&
            result.test_files.length > 0 && (
              <div>
                <strong>
                  Test files:
                </strong>

                <ul>
                  {result.test_files.map(
                    (file) => (
                      <li key={file}>
                        {file}
                      </li>
                    )
                  )}
                </ul>
              </div>
            )}

          <h4>Output</h4>

          <pre className="test-runner-output">
            {result.output ||
              result.stdout ||
              result.stderr ||
              "No output."}
          </pre>
        </div>
      )}
    </div>
  );
}
