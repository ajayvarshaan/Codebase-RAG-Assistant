import React, { useEffect, useState, type FormEvent } from "react";
import ReactMarkdown from "react-markdown";

import { askQuestion } from "./api/chat";

import {
  getProjectRelationships,
  type Relationship
} from "./api/relationships";
type Project = {
  id: number;
  name: string;
  description: string;
};


type CodeFile = {
  id: number;
  project_id: number;
  file_path: string;
  content: string;
};


type ChatSource = {
  chunk_id: number;
  file_id: number;
  file_path: string;
  start_line: number;
  end_line: number;
};


type ChatResponse = {
  answer: string;
  sources: ChatSource[];
};


type ChatMessage = {
  id: number;
  question: string;
  answer: string;
  sources: ChatSource[];
};


type ImpactFile = {
  file_id: number;
  file_path: string;
  relationship: string;
};


type CodeSearchResult = {
  file_id: number;
  file_path: string;
  line_number: number;
  line_content: string;
};


type CodeDiffResponse = {
  file_name: string;
  analysis: string;
};

type DocumentationResponse = {
  file_path: string;
  documentation: string;
};


type ReadmeResponse = {
  project_id: number;
  project_name: string;
  readme: string;
};

type TestRunResponse = {
  success: boolean;
  passed: number;
  failed: number;
  skipped: number;
  total: number;
  duration_seconds: number;
  output: string;
};


type FileTreeFolder = {
  name: string;
  path: string;
  folders: FileTreeFolder[];
  files: CodeFile[];
};


function buildFileTree(files: CodeFile[]): FileTreeFolder {
  const root: FileTreeFolder = {
    name: "Project",
    path: "",
    folders: [],
    files: []
  };

  for (const file of files) {
    const parts = file.file_path
      .split("/")
      .filter(Boolean);

    let current = root;
    let currentPath = "";

    parts.forEach((part, index) => {
      const isFile = index === parts.length - 1;

      if (isFile) {
        current.files.push(file);
        return;
      }

      currentPath = currentPath
        ? `${currentPath}/${part}`
        : part;

      let folder = current.folders.find(
        (item) => item.name === part
      );

      if (!folder) {
        folder = {
          name: part,
          path: currentPath,
          folders: [],
          files: []
        };

        current.folders.push(folder);
      }

      current = folder;
    });
  }

  const sortFolder = (folder: FileTreeFolder) => {
    folder.folders.sort((a, b) =>
      a.name.localeCompare(b.name)
    );

    folder.files.sort((a, b) =>
      a.file_path.localeCompare(b.file_path)
    );

    folder.folders.forEach(sortFolder);
  };

  sortFolder(root);

  return root;
}


type FileTreeProps = {
  files: CodeFile[];
  onOpenFile: (file: CodeFile) => void;
  onAnalyzeImpact: (file: CodeFile) => void;
  onExplainFile: (file: CodeFile) => void;
  onReviewCode: (file: CodeFile) => void;
  onGenerateTestCases: (file: CodeFile) => void;
  onGenerateCodeFix: (file: CodeFile) => void;
  onGenerateDocumentation: (file: CodeFile) => void;
};


function FileTree({
  files,
  onOpenFile,
  onAnalyzeImpact,
  onExplainFile,
  onReviewCode,
  onGenerateTestCases,
  onGenerateCodeFix,
  onGenerateDocumentation
}: FileTreeProps) {

  const [expanded, setExpanded] =
    useState<Record<string, boolean>>({});


  const tree = buildFileTree(files);


  const toggleFolder = (path: string) => {
    setExpanded((current) => ({
      ...current,
      [path]: !(current[path] ?? true)
    }));
  };


  const renderFolder = (
    folder: FileTreeFolder,
    depth: number
  ): React.ReactElement => {

    const isRoot = folder.path === "";
    const isExpanded =
      isRoot || (expanded[folder.path] ?? true);

    return (
      <div key={folder.path || "root"}>

        {!isRoot && (
          <button
            type="button"
            onClick={() =>
              toggleFolder(folder.path)
            }
            style={{
              display: "block",
              width: "100%",
              textAlign: "left",
              padding: "8px 12px",
              paddingLeft: `${12 + depth * 20}px`,
              marginBottom: "4px",
              border: "1px solid #444",
              borderRadius: "6px",
              background: "transparent",
              cursor: "pointer"
            }}
          >
            {isExpanded ? "📂" : "📁"}{" "}
            {folder.name}
          </button>
        )}


        {isExpanded && (
          <div>

            {folder.folders.map((child) =>
              renderFolder(
                child,
                isRoot ? 0 : depth + 1
              )
            )}


            {folder.files.map((file) => (
              <div
                key={file.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "8px",
                  padding: "8px 10px",
                  paddingLeft: `${16 + depth * 20}px`,
                  marginBottom: "6px",
                  border: "1px solid #333",
                  borderRadius: "6px"
                }}
              >

                <button
                  type="button"
                  onClick={() =>
                    onOpenFile(file)
                  }
                >
                  📄 {file.file_path}
                </button>


                <button
                  type="button"
                  onClick={() =>
                    onAnalyzeImpact(file)
                  }
                >
                  Analyze Impact
                </button>


                <button
                  type="button"
                  onClick={() =>
                    onExplainFile(file)
                  }
                >
                  Explain This File
                </button>


                <button
                  type="button"
                  onClick={() =>
                    onReviewCode(file)
                  }
                >
                  Review Code
                </button>


                <button
                  type="button"
                  onClick={() =>
                    onGenerateTestCases(file)
                  }
                >
                  Generate Test Cases
                </button>


                <button
                  type="button"
                  onClick={() =>
                    onGenerateCodeFix(file)
                  }
                >
                  Suggest Fix
                </button>


                <button
                  type="button"
                  onClick={() =>
                    onGenerateDocumentation(file)
                  }
                >
                  Generate Documentation
                </button>

              </div>
            ))}

          </div>
        )}

      </div>
    );
  };


  return (
    <div
      style={{
        padding: "15px",
        border: "1px solid #444",
        borderRadius: "10px",
        marginTop: "10px"
      }}
    >
      {renderFolder(tree, 0)}
    </div>
  );
}


function App() {

  // ---------------------------------------------------------
  // Projects
  // ---------------------------------------------------------

  const [projects, setProjects] = useState<Project[]>([]);

  const [message, setMessage] =
    useState("Loading projects...");

  const [loadingAction, setLoadingAction] =
    useState("");

  const [name, setName] = useState("");

  const [description, setDescription] =
    useState("");

  const [selectedProjectId, setSelectedProjectId] =
    useState<number | null>(null);


  // ---------------------------------------------------------
  // Code files
  // ---------------------------------------------------------

  const [files, setFiles] =
    useState<CodeFile[]>([]);

  const [fileMessage, setFileMessage] =
    useState("");

  const [selectedFile, setSelectedFile] =
    useState<CodeFile | null>(null);

  const [filePath, setFilePath] =
    useState("");

  const [fileContent, setFileContent] =
    useState("");


  // ---------------------------------------------------------
  // ZIP upload
  // ---------------------------------------------------------

  const [zipFile, setZipFile] =
    useState<File | null>(null);

  const [zipMessage, setZipMessage] =
    useState("");


  // ---------------------------------------------------------
  // Chat
  // ---------------------------------------------------------

  const [question, setQuestion] =
    useState("");

  const [chatMessage, setChatMessage] =
    useState("");


  // ---------------------------------------------------------
  // Chat history
  // ---------------------------------------------------------

  const [chatHistory, setChatHistory] =
    useState<ChatMessage[]>([]);


  // ---------------------------------------------------------
  // Relationships
  // ---------------------------------------------------------

  const [relationships, setRelationships] =
    useState<Relationship[]>([]);


  // ---------------------------------------------------------
  // Impact Analysis
  // ---------------------------------------------------------

  const [impactFile, setImpactFile] =
    useState<CodeFile | null>(null);

  const [affectedFiles, setAffectedFiles] =
    useState<ImpactFile[]>([]);

  const [impactMessage, setImpactMessage] =
    useState("");

  const [impactExplanation, setImpactExplanation] =
    useState("");


  // ---------------------------------------------------------
  // Architecture Summary
  // ---------------------------------------------------------

  const [architectureSummary, setArchitectureSummary] =
    useState("");

  const [architectureMessage, setArchitectureMessage] =
    useState("");

  const [showArchitectureSummary, setShowArchitectureSummary] =
    useState(false);


  // ---------------------------------------------------------
  // File Explanation
  // ---------------------------------------------------------

  const [fileExplanation, setFileExplanation] =
    useState("");

  const [fileExplanationMessage, setFileExplanationMessage] =
    useState("");

  const [explanationFile, setExplanationFile] =
    useState<CodeFile | null>(null);


  // ---------------------------------------------------------
  // Code Review
  // ---------------------------------------------------------

  const [codeReview, setCodeReview] =
    useState("");

  const [codeReviewMessage, setCodeReviewMessage] =
    useState("");

  const [reviewFile, setReviewFile] =
    useState<CodeFile | null>(null);


  // ---------------------------------------------------------
  // Test Case Generation
  // ---------------------------------------------------------

  const [testCases, setTestCases] =
    useState("");

  const [testCasesMessage, setTestCasesMessage] =
    useState("");

  const [testFile, setTestFile] =
    useState<CodeFile | null>(null);


  // ---------------------------------------------------------
  // AI Code Fix
  // ---------------------------------------------------------

  const [codeFix, setCodeFix] =
    useState("");

  const [codeFixMessage, setCodeFixMessage] =
    useState("");

  const [fixFile, setFixFile] =
    useState<CodeFile | null>(null);


  // ---------------------------------------------------------
  // Code Search
  // ---------------------------------------------------------

  const [searchQuery, setSearchQuery] =
    useState("");

  const [searchResults, setSearchResults] =
    useState<CodeSearchResult[]>([]);

  const [searchMessage, setSearchMessage] =
    useState("");


  // ---------------------------------------------------------
  // Code Diff Analysis
  // ---------------------------------------------------------

  const [diffFileName, setDiffFileName] =
    useState("");

  const [oldCode, setOldCode] =
    useState("");

  const [newCode, setNewCode] =
    useState("");

  const [diffAnalysis, setDiffAnalysis] =
    useState("");

  const [diffMessage, setDiffMessage] =
    useState("");


  // ---------------------------------------------------------
  // Documentation
  // ---------------------------------------------------------

  const [documentation, setDocumentation] =
    useState("");

  const [documentationMessage, setDocumentationMessage] =
    useState("");

  const [documentationFile, setDocumentationFile] =
    useState<CodeFile | null>(null);

  const [readme, setReadme] =
    useState("");

  const [readmeMessage, setReadmeMessage] =
    useState("");

  const [showReadme, setShowReadme] =
    useState(false);


  // ---------------------------------------------------------
  // Automated Tests
  // ---------------------------------------------------------

  const [testRun, setTestRun] =
    useState<TestRunResponse | null>(null);

  const [testRunMessage, setTestRunMessage] =
    useState("");


  // ---------------------------------------------------------
  // Selected source
  // ---------------------------------------------------------

  const [selectedSource, setSelectedSource] =
    useState<ChatSource | null>(null);


  // ---------------------------------------------------------
  // Load projects
  // ---------------------------------------------------------

  useEffect(() => {

    fetch(
      "http://127.0.0.1:8000/projects/"
    )
      .then((response) => {

        if (!response.ok) {
          throw new Error(
            "Could not load projects"
          );
        }

        return response.json();
      })
      .then((data) => {

        setProjects(data);

        setMessage("");
      })
      .catch(() => {

        setMessage(
          "Could not load projects"
        );
      });

  }, []);


  // ---------------------------------------------------------
  // Load files and relationships when project changes
  // ---------------------------------------------------------

  useEffect(() => {

    if (selectedProjectId === null) {

      setFiles([]);

      setRelationships([]);

      setFileMessage("");

      setChatHistory([]);

      setChatMessage("");

      setSelectedFile(null);

      setSelectedSource(null);

      setImpactFile(null);

      setAffectedFiles([]);

      setImpactMessage("");

      setImpactExplanation("");

      setArchitectureSummary("");

      setArchitectureMessage("");

      setShowArchitectureSummary(false);

      setFileExplanation("");

      setFileExplanationMessage("");

      setExplanationFile(null);

      setCodeReview("");
      setCodeReviewMessage("");
      setReviewFile(null);

       setTestCases("");
       setTestCasesMessage("");
       setTestFile(null);

       setCodeFix("");
       setCodeFixMessage("");
       setFixFile(null);

       setDocumentation("");
       setDocumentationMessage("");
       setDocumentationFile(null);

       setReadme("");
       setReadmeMessage("");
       setShowReadme(false);

       setTestRun(null);
       setTestRunMessage("");

       setSearchQuery("");
       setSearchResults([]);
       setSearchMessage("");

       setDiffFileName("");
       setOldCode("");
       setNewCode("");
       setDiffAnalysis("");
       setDiffMessage("");

      return;
    }


    // Load code files

    loadProjectFiles(
      selectedProjectId
    );


    // Load relationships

    loadProjectRelationships(
      selectedProjectId
    );


    // Clear old project chat

    setQuestion("");

    setChatHistory([]);

    setChatMessage("");

    setSelectedFile(null);

    setSelectedSource(null);

    setImpactFile(null);

    setAffectedFiles([]);

    setImpactMessage("");

    setImpactExplanation("");

    setArchitectureSummary("");

    setArchitectureMessage("");

    setShowArchitectureSummary(false);

    setFileExplanation("");

    setFileExplanationMessage("");

    setExplanationFile(null);

    setCodeReview("");
    setCodeReviewMessage("");
    setReviewFile(null);

       setTestCases("");
       setTestCasesMessage("");
       setTestFile(null);

       setCodeFix("");
       setCodeFixMessage("");
       setFixFile(null);

       setDocumentation("");
       setDocumentationMessage("");
       setDocumentationFile(null);

       setReadme("");
       setReadmeMessage("");
       setShowReadme(false);

       setSearchQuery("");
       setSearchResults([]);
       setSearchMessage("");

       setDiffFileName("");
       setOldCode("");
       setNewCode("");
       setDiffAnalysis("");
       setDiffMessage("");

  }, [selectedProjectId]);


  // ---------------------------------------------------------
  // Load project files
  // ---------------------------------------------------------

  const loadProjectFiles = (
    projectId: number
  ) => {

    setFiles([]);

    setFileMessage(
      "Loading code files..."
    );


    fetch(
      `http://127.0.0.1:8000/files/project/${projectId}`
    )
      .then((response) => {

        if (!response.ok) {
          throw new Error(
            "Could not load files"
          );
        }

        return response.json();
      })
      .then((data) => {

        setFiles(data);

        setFileMessage("");
      })
      .catch(() => {

        setFileMessage(
          "Could not load code files"
        );
      });
  };


  const finishLoading = () => {
    setLoadingAction("");
  };


  // ---------------------------------------------------------
  // Load project relationships
  // ---------------------------------------------------------

  const loadProjectRelationships = async (
    projectId: number
  ) => {

    try {

      const data =
        await getProjectRelationships(
          projectId
        );

      setRelationships(
        data.relationships
      );

    } catch (error) {

      console.error(
        "Failed to load relationships:",
        error
      );

      setRelationships([]);
    }
  };


  // ---------------------------------------------------------
  // Analyze file impact
  // ---------------------------------------------------------

  const analyzeImpact = async (
    file: CodeFile
  ) => {

    if (selectedProjectId === null) {
      return;
    }

    setLoadingAction("Analyzing file impact...");

    setImpactFile(file);

    setAffectedFiles([]);

    setImpactExplanation("");

    setImpactMessage(
      "Analyzing file impact..."
    );

    try {

      // Get affected files

      const impactResponse =
        await fetch(
          `http://127.0.0.1:8000/impact/project/${selectedProjectId}/file/${file.id}`
        );

      if (!impactResponse.ok) {
        throw new Error(
          "Could not analyze file impact"
        );
      }

      const impactData =
        await impactResponse.json();

      setAffectedFiles(
        impactData.affected_files || []
      );


      // Get AI explanation

      setLoadingAction("Generating AI impact explanation...");

      setImpactMessage(
        "Generating AI impact explanation..."
      );

      const explanationResponse =
        await fetch(
          `http://127.0.0.1:8000/impact-explanation/project/${selectedProjectId}/file/${file.id}`
        );

      if (!explanationResponse.ok) {
        throw new Error(
          "Could not generate impact explanation"
        );
      }

      const explanationData =
        await explanationResponse.json();

      setImpactExplanation(
        explanationData.explanation || ""
      );

      setImpactMessage("");

    } catch (error) {

      console.error(
        "Failed to analyze file impact:",
        error
      );

      setImpactMessage(
        "Could not analyze file impact."
      );
    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Explain selected file
  // ---------------------------------------------------------

  const explainFile = async (
    file: CodeFile
  ) => {

    if (selectedProjectId === null) {
      return;
    }

    setLoadingAction("Generating file explanation...");

    setExplanationFile(file);

    setFileExplanation("");

    setFileExplanationMessage(
      "Generating file explanation..."
    );

    try {

      const response =
        await fetch(
          `http://127.0.0.1:8000/file-explanation/project/${selectedProjectId}/file/${file.id}`
        );

      if (!response.ok) {
        throw new Error(
          "Could not generate file explanation"
        );
      }

      const data =
        await response.json();

      setFileExplanation(
        data.explanation || ""
      );

      setFileExplanationMessage("");

    } catch (error) {

      console.error(
        "Failed to generate file explanation:",
        error
      );

      setFileExplanationMessage(
        "Could not generate file explanation."
      );
    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Review selected file
  // ---------------------------------------------------------

  const reviewCodeFile = async (
    file: CodeFile
  ) => {

    if (selectedProjectId === null) {
      return;
    }

    setLoadingAction("Reviewing code with AI...");

    setReviewFile(file);

    setCodeReview("");

    setCodeReviewMessage(
      "Generating AI code review..."
    );

    try {

      const response =
        await fetch(
          `http://127.0.0.1:8000/code-review/project/${selectedProjectId}/file/${file.id}`
        );

      if (!response.ok) {
        throw new Error(
          "Could not generate code review"
        );
      }

      const data =
        await response.json();

      setCodeReview(
        data.review || ""
      );

      setCodeReviewMessage("");

    } catch (error) {

      console.error(
        "Failed to generate code review:",
        error
      );

      setCodeReviewMessage(
        "Could not generate code review."
      );
    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Generate test cases for selected file
  // ---------------------------------------------------------

  const generateTestCases = async (
    file: CodeFile
  ) => {

    if (selectedProjectId === null) {
      return;
    }

    setLoadingAction("Generating AI test cases...");

    setTestFile(file);
    setTestCases("");
    setTestCasesMessage("Generating AI test cases...");

    try {

      const response =
        await fetch(
          `http://127.0.0.1:8000/test-generation/project/${selectedProjectId}/file/${file.id}`
        );

      if (!response.ok) {
        throw new Error(
          "Could not generate test cases"
        );
      }

      const data = await response.json();

      setTestCases(
        data.test_cases || ""
      );

      setTestCasesMessage("");

    } catch (error) {

      console.error(
        "Failed to generate test cases:",
        error
      );

      setTestCasesMessage(
        "Could not generate test cases."
      );
    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Generate AI code fix
  // ---------------------------------------------------------

  const generateCodeFix = async (
    file: CodeFile
  ) => {

    if (selectedProjectId === null) {
      return;
    }

    setLoadingAction("Generating AI suggested fix...");

    setFixFile(file);
    setCodeFix("");
    setCodeFixMessage(
      "Generating AI suggested fix..."
    );

    try {

      const response = await fetch(
        `http://127.0.0.1:8000/code-fix/project/${selectedProjectId}/file/${file.id}`
      );

      if (!response.ok) {
        throw new Error(
          "Could not generate code fix"
        );
      }

      const data = await response.json();

      setCodeFix(data.fix || "");
      setCodeFixMessage("");

    } catch (error) {

      console.error(
        "Failed to generate code fix:",
        error
      );

      setCodeFixMessage(
        "Could not generate AI code fix."
      );
    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Search codebase
  // ---------------------------------------------------------

  const searchCodebase = async (
    event: FormEvent
  ) => {

    event.preventDefault();

    if (selectedProjectId === null) {
      return;
    }

    if (!searchQuery.trim()) {
      setSearchResults([]);
      setSearchMessage("Enter something to search.");
      return;
    }

    setLoadingAction("Searching codebase...");

    setSearchResults([]);
    setSearchMessage("Searching codebase...");

    try {

      const response = await fetch(
        `http://127.0.0.1:8000/code-search/project/${selectedProjectId}?query=${encodeURIComponent(searchQuery.trim())}`
      );

      if (!response.ok) {
        throw new Error("Could not search codebase");
      }

      const data = await response.json();

      setSearchResults(data.results || []);

      if ((data.results || []).length === 0) {
        setSearchMessage("No matching code found.");
      } else {
        setSearchMessage(
          `${data.results.length} matching result(s) found.`
        );
      }

    } catch (error) {

      console.error(
        "Failed to search codebase:",
        error
      );

      setSearchMessage(
        "Could not search the codebase."
      );
    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Analyze code diff
  // ---------------------------------------------------------

  const analyzeCodeDiff = async (
    event: FormEvent
  ) => {

    event.preventDefault();

    if (selectedProjectId === null) {
      return;
    }

    if (!oldCode.trim() || !newCode.trim()) {
      setDiffAnalysis("");
      setDiffMessage("Please provide both old code and new code.");
      return;
    }

    setLoadingAction("Analyzing code changes with AI...");
    setDiffAnalysis("");
    setDiffMessage("Analyzing code changes with AI...");

    try {

      const response = await fetch(
        `http://127.0.0.1:8000/code-diff/project/${selectedProjectId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            file_name: diffFileName.trim() || "Selected file",
            old_code: oldCode,
            new_code: newCode
          })
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail ||
          "Could not analyze code changes"
        );
      }

      const data: CodeDiffResponse = await response.json();

      setDiffAnalysis(data.analysis || "");
      setDiffMessage("");

    } catch (error) {

      console.error("Failed to analyze code diff:", error);

      setDiffMessage(
        error instanceof Error
          ? error.message
          : "Could not analyze code changes."
      );

    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Generate README for the selected project
  const generateReadme = async () => {

    if (!selectedProjectId) {
      return;
    }

    setLoadingAction("Generating project README with AI...");
    setReadme("");
    setReadmeMessage("");
    setShowReadme(true);

    try {

      const response = await fetch(
        `http://127.0.0.1:8000/readme/project/${selectedProjectId}`
      );

      const data: ReadmeResponse =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.readme ||
          "Could not generate README"
        );
      }

      setReadme(data.readme);

    } catch (error) {

      setReadmeMessage(
        error instanceof Error
          ? error.message
          : "Could not generate README."
      );

    } finally {

      setLoadingAction("");

    }
  };


  // Generate documentation for selected file
  // ---------------------------------------------------------

  const generateDocumentation = async (
    file: CodeFile
  ) => {

    if (selectedProjectId === null) {
      return;
    }

    setLoadingAction("Generating documentation with AI...");

    setDocumentationFile(file);
    setDocumentation("");
    setDocumentationMessage(
      "Generating AI documentation..."
    );

    try {

      const response = await fetch(
        `http://127.0.0.1:8000/documentation/project/${selectedProjectId}/file/${file.id}`
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail ||
          "Could not generate documentation"
        );
      }

      const data: DocumentationResponse =
        await response.json();

      setDocumentation(
        data.documentation || ""
      );

      setDocumentationMessage("");

    } catch (error) {

      console.error(
        "Failed to generate documentation:",
        error
      );

      setDocumentationMessage(
        error instanceof Error
          ? error.message
          : "Could not generate documentation."
      );

    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Generate architecture summary
  // ---------------------------------------------------------

  const generateArchitectureSummary = async () => {

    if (selectedProjectId === null) {
      return;
    }

    setLoadingAction("Analyzing project architecture...");

    setShowArchitectureSummary(true);

    setArchitectureSummary("");

    setArchitectureMessage(
      "Analyzing project architecture..."
    );

    try {

      const response =
        await fetch(
          `http://127.0.0.1:8000/architecture/project/${selectedProjectId}`
        );

      if (!response.ok) {
        throw new Error(
          "Could not generate architecture summary"
        );
      }

      const data =
        await response.json();

      setArchitectureSummary(
        data.summary || ""
      );

      setArchitectureMessage("");

    } catch (error) {

      console.error(
        "Failed to generate architecture summary:",
        error
      );

      setArchitectureMessage(
        "Could not generate architecture summary."
      );
    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Run automated tests
  // ---------------------------------------------------------

  const runAutomatedTests = async () => {
    setLoadingAction("Running automated tests...");
    setTestRun(null);
    setTestRunMessage("Running the backend test suite...");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/tests/run"
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail ||
          data?.output ||
          "Could not run automated tests."
        );
      }

      const result: TestRunResponse = data;
      setTestRun(result);
      setTestRunMessage(
        result.success
          ? `All ${result.total} automated tests passed.`
          : `${result.failed} test(s) failed.`
      );
    } catch (error) {
      console.error("Failed to run automated tests:", error);
      setTestRunMessage(
        error instanceof Error
          ? error.message
          : "Could not run automated tests."
      );
    } finally {
      finishLoading();
    }
  };

  // ---------------------------------------------------------
  // Create project
  // ---------------------------------------------------------

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {

    event.preventDefault();


    if (
      !name.trim() ||
      !description.trim()
    ) {

      setMessage(
        "Please enter a project name and description."
      );

      return;
    }


    setLoadingAction("Creating project...");

    setMessage(
      "Creating project..."
    );


    const params =
      new URLSearchParams({
        name: name.trim(),
        description: description.trim()
      });


    try {

      const response =
        await fetch(
          `http://127.0.0.1:8000/projects/?${params.toString()}`,
          {
            method: "POST"
          }
        );


      if (!response.ok) {

        throw new Error(
          "Could not create project"
        );
      }


      const newProject =
        await response.json();


      setProjects(
        (currentProjects) => [
          ...currentProjects,
          newProject
        ]
      );


      setName("");

      setDescription("");

      setMessage("");

    } catch {

      setMessage(
        "Could not create project"
      );
    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Add individual code file
  // ---------------------------------------------------------

  const handleFileSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {

    event.preventDefault();


    if (
      selectedProjectId === null ||
      !filePath.trim() ||
      !fileContent.trim()
    ) {

      setFileMessage(
        "Please enter both a file path and code content."
      );

      return;
    }


    setLoadingAction("Adding code file...");

    setFileMessage(
      "Adding code file..."
    );


    try {

      const response =
        await fetch(
          "http://127.0.0.1:8000/files/",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body: JSON.stringify({
              project_id:
                selectedProjectId,

              file_path:
                filePath.trim(),

              content:
                fileContent
            })
          }
        );


      if (!response.ok) {

        throw new Error(
          "Could not add code file"
        );
      }


      const newFile =
        await response.json();


      setFiles(
        (currentFiles) => [
          ...currentFiles,
          newFile
        ]
      );


      setFilePath("");

      setFileContent("");

      setFileMessage("");


      // Reload relationships because
      // a new file may create relationships

      await loadProjectRelationships(
        selectedProjectId
      );

    } catch {

      setFileMessage(
        "Could not add code file"
      );
    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Upload project ZIP
  // ---------------------------------------------------------

  const handleZipUpload = async (
    event: FormEvent<HTMLFormElement>
  ) => {

    event.preventDefault();


    if (selectedProjectId === null) {

      setZipMessage(
        "Please select a project first."
      );

      return;
    }


    if (!zipFile) {

      setZipMessage(
        "Please select a ZIP file."
      );

      return;
    }


    setLoadingAction("Uploading and indexing ZIP...");

    setZipMessage(
      "Uploading and indexing ZIP..."
    );


    const formData =
      new FormData();


    formData.append(
      "file",
      zipFile
    );


    try {

      const response =
        await fetch(
          `http://127.0.0.1:8000/files/upload-zip/${selectedProjectId}`,
          {
            method: "POST",
            body: formData
          }
        );


      if (!response.ok) {

        throw new Error(
          "Could not upload ZIP"
        );
      }


      const data =
        await response.json();


      setZipMessage(
        `Successfully indexed ${data.files_processed} files and ${data.chunks_created} chunks.`
      );


      setZipFile(null);


      // Reload files

      loadProjectFiles(
        selectedProjectId
      );


      // Reload relationships

      await loadProjectRelationships(
        selectedProjectId
      );


      setSelectedFile(null);

      setSelectedSource(null);

      setImpactFile(null);

      setAffectedFiles([]);

      setImpactMessage("");

      setImpactExplanation("");

      setArchitectureSummary("");

      setArchitectureMessage("");

      setShowArchitectureSummary(false);

      setFileExplanation("");

      setFileExplanationMessage("");

      setExplanationFile(null);

      setCodeReview("");
      setCodeReviewMessage("");
      setReviewFile(null);

      setTestCases("");
      setTestCasesMessage("");
      setTestFile(null);

      setCodeFix("");
      setCodeFixMessage("");
      setFixFile(null);

      setDocumentation("");
      setDocumentationMessage("");
      setDocumentationFile(null);

      setReadme("");
      setReadmeMessage("");
      setShowReadme(false);

      setSearchResults([]);
      setSearchMessage("");

      setDiffAnalysis("");
      setDiffMessage("");

      // Clear old chat because
      // the codebase changed

      setChatHistory([]);

      setChatMessage("");

    } catch {

      setZipMessage(
        "Could not upload ZIP file."
      );
    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Ask AI
  // ---------------------------------------------------------

  const handleChatSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {

    event.preventDefault();


    if (selectedProjectId === null) {

      setChatMessage(
        "Please select a project first."
      );

      return;
    }


    if (!question.trim()) {

      setChatMessage(
        "Please enter a question."
      );

      return;
    }


    const currentQuestion =
      question.trim();


    setLoadingAction("Thinking...");

    setChatMessage(
      "Thinking..."
    );


    try {

      // Convert existing chat history
      // into user/assistant messages

      const conversationHistory =
        chatHistory.flatMap(
          (chat) => [
            {
              role: "user" as const,
              content:
                chat.question
            },

            {
              role: "assistant" as const,
              content:
                chat.answer
            }
          ]
        );


      const data: ChatResponse =
        await askQuestion(
          selectedProjectId,
          currentQuestion,
          conversationHistory
        );


      const newMessage: ChatMessage = {

        id: Date.now(),

        question:
          currentQuestion,

        answer:
          data.answer,

        sources:
          data.sources
      };


      setChatHistory(
        (currentHistory) => [
          ...currentHistory,
          newMessage
        ]
      );


      // Clear question box

      setQuestion("");

      setChatMessage("");

    } catch {

      setChatMessage(
        "Could not get an answer."
      );
    } finally {
      finishLoading();
    }
  };


  // ---------------------------------------------------------
  // Clear chat
  // ---------------------------------------------------------

  const clearChat = () => {

    setChatHistory([]);

    setQuestion("");

    setChatMessage("");

    setSelectedSource(null);
  };


  // ---------------------------------------------------------
  // Open normal file
  // ---------------------------------------------------------

  const openFile = (
    file: CodeFile
  ) => {

    setSelectedFile(file);

    setSelectedSource(null);

    setImpactFile(null);

    setAffectedFiles([]);

    setImpactMessage("");

    setImpactExplanation("");

    setArchitectureSummary("");

    setArchitectureMessage("");

    setShowArchitectureSummary(false);

    setFileExplanation("");

    setFileExplanationMessage("");

    setExplanationFile(null);

    setCodeReview("");
    setCodeReviewMessage("");
    setReviewFile(null);

    setTestCases("");
    setTestCasesMessage("");
    setTestFile(null);

    setCodeFix("");
    setCodeFixMessage("");
    setFixFile(null);

    setDocumentation("");
    setDocumentationMessage("");
    setDocumentationFile(null);

    setReadme("");
    setReadmeMessage("");
    setShowReadme(false);

    setTestRun(null);
    setTestRunMessage("");

    setDiffAnalysis("");
    setDiffMessage("");


    setTimeout(() => {

      document
        .getElementById(
          "source-viewer"
        )
        ?.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });

    }, 100);
  };


  // ---------------------------------------------------------
  // Open source chunk
  // ---------------------------------------------------------

  const openSource = (
    source: ChatSource
  ) => {

    setSelectedSource(source);

    setSelectedFile(null);

    setImpactFile(null);

    setAffectedFiles([]);

    setImpactMessage("");

    setImpactExplanation("");

    setArchitectureSummary("");

    setArchitectureMessage("");

    setShowArchitectureSummary(false);

    setFileExplanation("");

    setFileExplanationMessage("");

    setExplanationFile(null);

    setCodeReview("");
    setCodeReviewMessage("");
    setReviewFile(null);

    setTestCases("");
    setTestCasesMessage("");
    setTestFile(null);

    setCodeFix("");
    setCodeFixMessage("");
    setFixFile(null);

    setDocumentation("");
    setDocumentationMessage("");
    setDocumentationFile(null);

    setReadme("");
    setReadmeMessage("");
    setShowReadme(false);

    setDiffAnalysis("");
    setDiffMessage("");


    setTimeout(() => {

      document
        .getElementById(
          "source-viewer"
        )
        ?.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });

    }, 100);
  };


  // ---------------------------------------------------------
  // Get selected source code
  // ---------------------------------------------------------

  const getSelectedSourceCode = () => {

    if (!selectedSource) {

      return [];
    }


    const file =
      files.find(
        (currentFile) =>
          currentFile.id ===
          selectedSource.file_id
      );


    if (!file) {

      return [];
    }


    const lines =
      file.content.split("\n");


    return lines
      .slice(
        selectedSource.start_line - 1,
        selectedSource.end_line
      )
      .map(
        (line, index) => ({
          number:
            selectedSource.start_line +
            index,

          content:
            line
        })
      );
  };


  const selectedSourceCode =
    getSelectedSourceCode();


  // ---------------------------------------------------------
  // UI
  // ---------------------------------------------------------

  return (

    <div>

      <h1>
        Codebase RAG Assistant
      </h1>


      {loadingAction && (
        <div
          style={{
            margin: "15px 0",
            padding: "12px 16px",
            border: "1px solid #888",
            borderRadius: "8px",
            fontWeight: "bold"
          }}
        >
          ⏳ {loadingAction}
        </div>
      )}


      {/* =====================================================
          CREATE PROJECT
          ===================================================== */}

      <h2>
        Add a Project
      </h2>


      <form
        onSubmit={handleSubmit}
      >

        <input
          type="text"
          placeholder="Project name"
          value={name}
          onChange={(event) =>
            setName(
              event.target.value
            )
          }
        />


        <input
          type="text"
          placeholder="Project description"
          value={description}
          onChange={(event) =>
            setDescription(
              event.target.value
            )
          }
        />


        <button type="submit">
          Add Project
        </button>

      </form>


      {/* =====================================================
          PROJECTS
          ===================================================== */}

      <h2>
        Projects
      </h2>


      {message && (
        <p>
          {message}
        </p>
      )}


      {projects.map(
        (project) => (

          <div key={project.id}>

            <h3>

              <button
                type="button"
                onClick={() =>
                  setSelectedProjectId(
                    project.id
                  )
                }
              >
                {project.name}
              </button>

            </h3>


            <p>
              {project.description}
            </p>


            {selectedProjectId ===
              project.id && (

              <p>
                Selected project:
                {" "}
                {project.name}
              </p>

            )}

          </div>

        )
      )}


      {/* =====================================================
          SELECTED PROJECT
          ===================================================== */}

      {selectedProjectId !== null && (

        <section>

          {/* =================================================
              PROJECT DASHBOARD
              ================================================= */}

          <div
            style={{
              marginTop: "20px",
              marginBottom: "25px",
              padding: "20px",
              border: "1px solid #555",
              borderRadius: "12px"
            }}
          >

            <h2>
              📊 Project Dashboard
            </h2>

            <p>
              Overview of your indexed codebase and available AI tools.
            </p>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: "12px",
                marginTop: "15px"
              }}
            >

              <div
                style={{
                  padding: "16px",
                  border: "1px solid #555",
                  borderRadius: "8px"
                }}
              >
                <strong>📄 Files</strong>
                <div style={{ fontSize: "24px", marginTop: "8px" }}>
                  {files.length}
                </div>
              </div>

              <div
                style={{
                  padding: "16px",
                  border: "1px solid #555",
                  borderRadius: "8px"
                }}
              >
                <strong>🔗 Relationships</strong>
                <div style={{ fontSize: "24px", marginTop: "8px" }}>
                  {relationships.length}
                </div>
              </div>

              <div
                style={{
                  padding: "16px",
                  border: "1px solid #555",
                  borderRadius: "8px"
                }}
              >
                <strong>💬 Chat Messages</strong>
                <div style={{ fontSize: "24px", marginTop: "8px" }}>
                  {chatHistory.length}
                </div>
              </div>

              <div
                style={{
                  padding: "16px",
                  border: "1px solid #555",
                  borderRadius: "8px"
                }}
              >
                <strong>🛠️ AI Tools</strong>
                <div style={{ fontSize: "24px", marginTop: "8px" }}>
                  12
                </div>
              </div>

            </div>

            <h3 style={{ marginTop: "25px" }}>
              AI Developer Tools
            </h3>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "8px"
              }}
            >
              <button
                type="button"
                onClick={generateArchitectureSummary}
              >
                🏗️ Architecture
              </button>

              <button
                type="button"
                onClick={() => {
                  document.getElementById("code-search-section")?.scrollIntoView({
                    behavior: "smooth"
                  });
                }}
              >
                🔎 Code Search
              </button>

              <button
                type="button"
                onClick={() => {
                  document.getElementById("code-diff-section")?.scrollIntoView({
                    behavior: "smooth"
                  });
                }}
              >
                🔄 Code Diff
              </button>

              <button
                type="button"
                onClick={() => {
                  document.getElementById("code-files-section")?.scrollIntoView({
                    behavior: "smooth"
                  });
                }}
              >
                📄 Code Files
              </button>

              <button
                type="button"
                onClick={() => {
                  document.getElementById("chat-section")?.scrollIntoView({
                    behavior: "smooth"
                  });
                }}
              >
                💬 RAG Chat
              </button>

              <button
                type="button"
                onClick={() => {
                  document.getElementById("code-files-section")?.scrollIntoView({
                    behavior: "smooth"
                  });
                }}
              >
                💥 Impact Analysis
              </button>

              <button
                type="button"
                onClick={() => {
                  document.getElementById("code-files-section")?.scrollIntoView({
                    behavior: "smooth"
                  });
                }}
              >
                📖 File Explanation
              </button>

              <button
                type="button"
                onClick={() => {
                  document.getElementById("code-files-section")?.scrollIntoView({
                    behavior: "smooth"
                  });
                }}
              >
                🤖 Code Review
              </button>

              <button
                type="button"
                onClick={() => {
                  document.getElementById("code-files-section")?.scrollIntoView({
                    behavior: "smooth"
                  });
                }}
              >
                🧪 Test Generation
              </button>

              <button
                type="button"
                onClick={() => {
                  document.getElementById("code-files-section")?.scrollIntoView({
                    behavior: "smooth"
                  });
                }}
              >
                🛠️ Code Fix
              </button>

              <button
                type="button"
                onClick={() => {
                  document.getElementById("code-files-section")?.scrollIntoView({
                    behavior: "smooth"
                  });
                }}
              >
                📚 Documentation
              </button>

              <button
                type="button"
                onClick={generateReadme}
              >
                📖 Generate README
              </button>

              <button
                type="button"
                onClick={() => {
                  document.getElementById("automated-tests-section")?.scrollIntoView({
                    behavior: "smooth"
                  });
                }}
              >
                🧪 Automated Tests
              </button>
            </div>

          </div>



          {/* =================================================
              AUTOMATED TESTS
              ================================================= */}

          <div id="automated-tests-section">

            <hr />

            <h2>
              🧪 Automated Tests
            </h2>

            <p>
              Run the backend automated test suite and view the results directly in the dashboard.
            </p>

            <button
              type="button"
              onClick={runAutomatedTests}
              disabled={loadingAction === "Running automated tests..."}
            >
              {loadingAction === "Running automated tests..."
                ? "⏳ Running Tests..."
                : "🧪 Run Automated Tests"}
            </button>

            {testRunMessage && (
              <p>
                {testRunMessage}
              </p>
            )}

            {testRun && (
              <div
                style={{
                  marginTop: "20px",
                  marginBottom: "20px",
                  padding: "20px",
                  border: "1px solid #555",
                  borderRadius: "8px"
                }}
              >
                <h3>
                  {testRun.success
                    ? "✅ Test Suite Passed"
                    : "❌ Test Suite Failed"}
                </h3>

                <p>
                  <strong>Total:</strong> {testRun.total}
                  {" | "}
                  <strong>Passed:</strong> {testRun.passed}
                  {" | "}
                  <strong>Failed:</strong> {testRun.failed}
                  {" | "}
                  <strong>Skipped:</strong> {testRun.skipped}
                </p>

                <p>
                  <strong>Duration:</strong> {testRun.duration_seconds}s
                </p>

                <h3>Test Output</h3>

                <pre
                  style={{
                    textAlign: "left",
                    overflowX: "auto",
                    whiteSpace: "pre-wrap",
                    padding: "15px",
                    border: "1px solid #333",
                    borderRadius: "6px"
                  }}
                >
                  {testRun.output || "No test output returned."}
                </pre>
              </div>
            )}

          </div>

          {/* =================================================
              CODE DIFF ANALYSIS
              ================================================= */}

          <div id="code-diff-section">

            <hr />

            <h2>
              🔄 AI Code Diff Analysis
            </h2>

            <p>
              Compare an old and new version of code and let AI explain
              the changes, risks, affected behavior, and recommended checks.
            </p>

            <form onSubmit={analyzeCodeDiff}>

              <input
                type="text"
                placeholder="File name (optional)"
                value={diffFileName}
                onChange={(event) =>
                  setDiffFileName(event.target.value)
                }
                style={{
                  width: "60%",
                  padding: "10px",
                  marginBottom: "12px"
                }}
              />

              <h3>Old Code</h3>

              <textarea
                value={oldCode}
                onChange={(event) =>
                  setOldCode(event.target.value)
                }
                placeholder="Paste the previous version of the code..."
                rows={12}
                style={{
                  width: "100%",
                  padding: "12px",
                  fontFamily: "monospace",
                  boxSizing: "border-box"
                }}
              />

              <h3>New Code</h3>

              <textarea
                value={newCode}
                onChange={(event) =>
                  setNewCode(event.target.value)
                }
                placeholder="Paste the new version of the code..."
                rows={12}
                style={{
                  width: "100%",
                  padding: "12px",
                  fontFamily: "monospace",
                  boxSizing: "border-box"
                }}
              />

              <button
                type="submit"
                style={{
                  marginTop: "12px"
                }}
              >
                🔄 Analyze Changes
              </button>

            </form>

            {diffMessage && (
              <p>
                {diffMessage}
              </p>
            )}

            {diffAnalysis && (
              <div
                style={{
                  marginTop: "20px",
                  marginBottom: "20px",
                  padding: "20px",
                  border: "1px solid #555",
                  borderRadius: "8px"
                }}
              >

                <h2>
                  🔄 AI Change Analysis
                </h2>

                {diffFileName && (
                  <p>
                    <strong>File:</strong>{" "}
                    {diffFileName}
                  </p>
                )}

                <ReactMarkdown>
                  {diffAnalysis}
                </ReactMarkdown>

              </div>
            )}

          </div>


          {/* =================================================
              CODE SEARCH
              ================================================= */}

          <div id="code-search-section">
          <hr />

          <h2>
            🔎 Find Anything in Code
          </h2>

          <form
            onSubmit={searchCodebase}
          >

            <input
              type="text"
              placeholder="Search file names, functions, imports, code..."
              value={searchQuery}
              onChange={(event) =>
                setSearchQuery(event.target.value)
              }
              style={{
                width: "60%",
                padding: "10px"
              }}
            />

            <button
              type="submit"
              style={{
                marginLeft: "10px"
              }}
            >
              Search Code
            </button>

          </form>

          {searchMessage && (
            <p>
              {searchMessage}
            </p>
          )}

          {searchResults.length > 0 && (
            <div
              style={{
                marginTop: "15px",
                marginBottom: "20px"
              }}
            >

              {searchResults.map(
                (result, index) => (

                  <div
                    key={`${result.file_id}-${result.line_number}-${index}`}
                    style={{
                      marginBottom: "12px",
                      padding: "12px",
                      border: "1px solid #555",
                      borderRadius: "8px"
                    }}
                  >

                    <button
                      type="button"
                      onClick={() => {
                        const file = files.find(
                          (item) =>
                            item.id === result.file_id
                        );

                        if (file) {
                          openFile(file);
                        }
                      }}
                    >
                      📄 {result.file_path}
                    </button>

                    <span
                      style={{
                        marginLeft: "10px"
                      }}
                    >
                      Line {result.line_number}
                    </span>

                    <pre
                      style={{
                        marginTop: "8px",
                        whiteSpace: "pre-wrap"
                      }}
                    >
                      {result.line_content}
                    </pre>

                  </div>

                )
              )}

            </div>
          )}


          </div>

          {/* =================================================
              ARCHITECTURE SUMMARY
              ================================================= */}

          <hr />

          <h2>
            Project Architecture
          </h2>

          <button
            type="button"
            onClick={generateArchitectureSummary}
          >
            🤖 Analyze Project Architecture
          </button>


          {showArchitectureSummary && (

            <div
              style={{
                marginTop: "20px",
                marginBottom: "20px",
                padding: "20px",
                border: "1px solid #555",
                borderRadius: "8px"
              }}
            >

              <h3>
                🏗️ Architecture Summary
              </h3>


              {architectureMessage && (
                <p>
                  {architectureMessage}
                </p>
              )}


              {architectureSummary && (
                <ReactMarkdown>
                  {architectureSummary}
                </ReactMarkdown>
              )}


              {!architectureMessage &&
                !architectureSummary && (

                  <p>
                    No architecture summary available.
                  </p>

                )}


              <button
                type="button"
                onClick={() => {
                  setShowArchitectureSummary(false);
                  setArchitectureSummary("");
                  setArchitectureMessage("");
                }}
                style={{
                  marginTop: "10px"
                }}
              >
                Close Architecture Summary
              </button>

            </div>

          )}


          {/* =================================================
              ZIP UPLOAD
              ================================================= */}

          <hr />

          <h2>
            Upload Project ZIP
          </h2>


          <form
            onSubmit={handleZipUpload}
          >

            <input
              type="file"
              accept=".zip"
              onChange={(event) => {

                const selectedFile =
                  event.target.files?.[0] ||
                  null;

                setZipFile(
                  selectedFile
                );

              }}
            />


            <br />
            <br />


            <button type="submit">
              Upload ZIP
            </button>

          </form>


          {zipMessage && (
            <p>
              {zipMessage}
            </p>
          )}


          {/* =================================================
              ADD INDIVIDUAL FILE
              ================================================= */}

          <hr />

          <h2>
            Add a Code File
          </h2>


          <form
            onSubmit={handleFileSubmit}
          >

            <input
              type="text"
              placeholder="File path, e.g. src/App.tsx"
              value={filePath}
              onChange={(event) =>
                setFilePath(
                  event.target.value
                )
              }
            />


            <br />


            <textarea
              placeholder="Paste the file's code here"
              value={fileContent}
              onChange={(event) =>
                setFileContent(
                  event.target.value
                )
              }
              rows={10}
              cols={50}
            />


            <br />


            <button type="submit">
              Add Code File
            </button>

          </form>


          {/* =================================================
              CODE FILES
              ================================================= */}

          {/* =================================================
              AI README GENERATOR
              ================================================= */}

          {showReadme && (

            <div
              style={{
                marginTop: "20px",
                marginBottom: "20px",
                padding: "20px",
                border: "1px solid #555",
                borderRadius: "8px"
              }}
            >

              <h2>
                📖 AI Generated README
              </h2>

              {readmeMessage && (
                <p>
                  {readmeMessage}
                </p>
              )}

              {readme && (
                <ReactMarkdown>
                  {readme}
                </ReactMarkdown>
              )}

              <button
                type="button"
                onClick={() => {
                  setShowReadme(false);
                  setReadme("");
                  setReadmeMessage("");
                }}
                style={{
                  marginTop: "10px"
                }}
              >
                Close README
              </button>

            </div>

          )}


          <h2>
            <span id="code-files-section">Code Files</span>
          </h2>


          {fileMessage && (
            <p>
              {fileMessage}
            </p>
          )}


          {!fileMessage &&
            files.length === 0 && (

              <p>
                No code files have been
                added to this project yet.
              </p>

            )}


          {files.length > 0 && (

            <FileTree
              files={files}
              onOpenFile={openFile}
              onAnalyzeImpact={analyzeImpact}
              onExplainFile={explainFile}
              onReviewCode={reviewCodeFile}
              onGenerateTestCases={generateTestCases}
              onGenerateCodeFix={generateCodeFix}
              onGenerateDocumentation={generateDocumentation}
            />

          )}


          {/* =================================================
              AI DOCUMENTATION
              ================================================= */}

          {documentationFile && (

            <div
              style={{
                marginTop: "20px",
                marginBottom: "20px",
                padding: "20px",
                border: "1px solid #555",
                borderRadius: "8px"
              }}
            >

              <h2>
                📚 AI Documentation
              </h2>

              <p>
                <strong>
                  File:
                </strong>{" "}
                {documentationFile.file_path}
              </p>

              {documentationMessage && (
                <p>
                  {documentationMessage}
                </p>
              )}

              {documentation && (
                <ReactMarkdown>
                  {documentation}
                </ReactMarkdown>
              )}

              <button
                type="button"
                onClick={() => {
                  setDocumentationFile(null);
                  setDocumentation("");
                  setDocumentationMessage("");
                }}
                style={{
                  marginTop: "10px"
                }}
              >
                Close Documentation
              </button>

            </div>

          )}


          {/* =================================================
              FILE EXPLANATION
              ================================================= */}

          {explanationFile && (

            <div
              style={{
                marginTop: "20px",
                marginBottom: "20px",
                padding: "20px",
                border: "1px solid #555",
                borderRadius: "8px"
              }}
            >

              <h2>
                🤖 File Explanation
              </h2>


              <p>
                <strong>
                  File:
                </strong>{" "}
                {explanationFile.file_path}
              </p>


              {fileExplanationMessage && (
                <p>
                  {fileExplanationMessage}
                </p>
              )}


              {fileExplanation && (
                <ReactMarkdown>
                  {fileExplanation}
                </ReactMarkdown>
              )}


              <button
                type="button"
                onClick={() => {
                  setExplanationFile(null);
                  setFileExplanation("");
                  setFileExplanationMessage("");
                }}
                style={{
                  marginTop: "10px"
                }}
              >
                Close File Explanation
              </button>

            </div>

          )}


          {/* =================================================
              CODE REVIEW
              ================================================= */}

          {reviewFile && (

            <div
              style={{
                marginTop: "20px",
                marginBottom: "20px",
                padding: "20px",
                border: "1px solid #555",
                borderRadius: "8px"
              }}
            >

              <h2>
                🤖 AI Code Review
              </h2>

              <p>
                <strong>
                  File:
                </strong>{" "}
                {reviewFile.file_path}
              </p>

              {codeReviewMessage && (
                <p>
                  {codeReviewMessage}
                </p>
              )}

              {codeReview && (
                <ReactMarkdown>
                  {codeReview}
                </ReactMarkdown>
              )}

              <button
                type="button"
                onClick={() => {
                  setReviewFile(null);
                  setCodeReview("");
                  setCodeReviewMessage("");
                }}
                style={{
                  marginTop: "10px"
                }}
              >
                Close Code Review
              </button>

            </div>

          )}


          {/* =================================================
              TEST CASE GENERATION
              ================================================= */}

          {testFile && (

            <div
              style={{
                marginTop: "20px",
                marginBottom: "20px",
                padding: "20px",
                border: "1px solid #555",
                borderRadius: "8px"
              }}
            >

              <h2>
                🧪 AI Test Case Generation
              </h2>

              <p>
                <strong>
                  File:
                </strong>{" "}
                {testFile.file_path}
              </p>

              {testCasesMessage && (
                <p>
                  {testCasesMessage}
                </p>
              )}

              {testCases && (
                <ReactMarkdown>
                  {testCases}
                </ReactMarkdown>
              )}

              <button
                type="button"
                onClick={() => {
                  setTestFile(null);
                  setTestCases("");
                  setTestCasesMessage("");
                }}
                style={{
                  marginTop: "10px"
                }}
              >
                Close Test Cases
              </button>

            </div>

          )}

          {/* =================================================
              AI CODE FIX
              ================================================= */}

          {fixFile && (

            <div
              style={{
                marginTop: "20px",
                marginBottom: "20px",
                padding: "20px",
                border: "1px solid #555",
                borderRadius: "8px"
              }}
            >

              <h2>
                🛠️ AI Suggested Fix
              </h2>

              <p>
                <strong>
                  File:
                </strong>{" "}
                {fixFile.file_path}
              </p>

              {codeFixMessage && (
                <p>
                  {codeFixMessage}
                </p>
              )}

              {codeFix && (
                <ReactMarkdown>
                  {codeFix}
                </ReactMarkdown>
              )}

              <button
                type="button"
                onClick={() => {
                  setFixFile(null);
                  setCodeFix("");
                  setCodeFixMessage("");
                }}
                style={{
                  marginTop: "10px"
                }}
              >
                Close Suggested Fix
              </button>

            </div>

          )}

          {/* =================================================
              IMPACT ANALYSIS
              ================================================= */}

          {impactFile && (

            <div
              style={{
                marginTop: "20px",
                marginBottom: "20px",
                padding: "15px",
                border: "1px solid #555",
                borderRadius: "8px"
              }}
            >

              <h2>
                Impact Analysis
              </h2>


              <p>
                <strong>
                  File:
                </strong>{" "}
                {impactFile.file_path}
              </p>


              {impactMessage && (
                <p>
                  {impactMessage}
                </p>
              )}


              {!impactMessage &&
                affectedFiles.length === 0 && (

                  <p>
                    No potentially affected files found.
                  </p>

                )}


              {affectedFiles.length > 0 && (

                <div>

                  <h3>
                    Potentially affected files:
                  </h3>


                  {affectedFiles.map(
                    (affectedFile) => {

                      const file =
                        files.find(
                          (currentFile) =>
                            currentFile.id ===
                            affectedFile.file_id
                        );

                      return (
                        <div
                          key={
                            affectedFile.file_id
                          }
                          style={{
                            marginBottom: "8px"
                          }}
                        >

                          <button
                            type="button"
                            onClick={() => {
                              if (file) {
                                openFile(file);
                              }
                            }}
                          >
                            📄{" "}
                            {affectedFile.file_path}
                          </button>

                        </div>
                      );
                    }
                  )}

                </div>

              )}


              {impactExplanation && (

                <div
                  style={{
                    marginTop: "20px",
                    padding: "15px",
                    border: "1px solid #555",
                    borderRadius: "8px"
                  }}
                >

                  <h3>
                    🤖 AI Impact Explanation
                  </h3>

                  <ReactMarkdown>
                    {impactExplanation}
                  </ReactMarkdown>

                </div>

              )}


              <button
                type="button"
                onClick={() => {
                  setImpactFile(null);
                  setAffectedFiles([]);
                  setImpactMessage("");
                  setImpactExplanation("");
                }}
                style={{
                  marginTop: "10px"
                }}
              >
                Close Impact Analysis
              </button>

            </div>

          )}


          {/* =================================================
              DEPENDENCY GRAPH
              ================================================= */}

          <hr />

          <h2>
            Codebase Dependencies
          </h2>


          {relationships.length === 0 ? (

            <p>
              No code relationships found
              for this project.
            </p>

          ) : (

            <div>

              {relationships.map(
                (relationship) => {

                  const sourceFile = files.find(
                    (file) =>
                      file.id ===
                      relationship.source_file_id
                  );

                  const targetFile = files.find(
                    (file) =>
                      file.id ===
                      relationship.target_file_id
                  );

                  return (
                    <div
                      key={relationship.id}
                      style={{
                        marginBottom: "15px",
                        padding: "15px",
                        border: "1px solid #555",
                        borderRadius: "8px"
                      }}
                    >

                      <div
                        style={{
                          marginBottom: "10px"
                        }}
                      >
                        <button
                          type="button"
                          onClick={() => {
                            if (sourceFile) {
                              openFile(sourceFile);
                            }
                          }}
                        >
                          📄 {relationship.source_file}
                        </button>
                      </div>

                      <div
                        style={{
                          marginLeft: "20px",
                          marginBottom: "10px"
                        }}
                      >
                        <span>
                          └── {relationship.relationship_type} →
                        </span>
                      </div>

                      <div
                        style={{
                          marginLeft: "40px"
                        }}
                      >
                        <button
                          type="button"
                          onClick={() => {
                            if (targetFile) {
                              openFile(targetFile);
                            }
                          }}
                        >
                          📄 {relationship.target_file}
                        </button>
                      </div>

                      <div
                        style={{
                          marginTop: "15px",
                          marginLeft: "20px"
                        }}
                      >
                        <span>
                          ← imported by ──
                        </span>

                        <button
                          type="button"
                          onClick={() => {
                            if (sourceFile) {
                              openFile(sourceFile);
                            }
                          }}
                          style={{
                            marginLeft: "8px"
                          }}
                        >
                          {relationship.source_file}
                        </button>
                      </div>

                    </div>
                  );
                }
              )}

            </div>

          )}


          {/* =================================================
              NORMAL FILE VIEWER
              ================================================= */}

          {selectedFile && (

            <div>

              <hr />


              <h3>
                {selectedFile.file_path}
              </h3>


              <pre
                style={{
                  textAlign: "left",
                  overflowX: "auto",
                  padding: "20px",
                  lineHeight: "1.6"
                }}
              >

                <code>
                  {selectedFile.content}
                </code>

              </pre>


              <button
                type="button"
                onClick={() =>
                  setSelectedFile(null)
                }
              >
                Close File
              </button>

            </div>

          )}


          {/* =================================================
              CHAT
              ================================================= */}

          <hr />

          <h2 id="chat-section">
            Ask About Your Code
          </h2>


          <form
            onSubmit={handleChatSubmit}
          >

            <textarea
              placeholder="Ask a question about this codebase..."
              value={question}
              onChange={(event) =>
                setQuestion(
                  event.target.value
                )
              }
              rows={5}
              cols={60}
            />


            <br />


            <button type="submit">
              Ask AI
            </button>


            {chatHistory.length > 0 && (

              <button
                type="button"
                onClick={clearChat}
                style={{
                  marginLeft:
                    "10px"
                }}
              >
                Clear Chat
              </button>

            )}

          </form>


          {chatMessage && (
            <p>
              {chatMessage}
            </p>
          )}


          {/* =================================================
              CHAT HISTORY
              ================================================= */}

          {chatHistory.length > 0 && (

            <div>

              <h2>
                Conversation
              </h2>


              {chatHistory.map(
                (chat) => (

                  <div
                    key={chat.id}
                    style={{
                      marginBottom:
                        "30px"
                    }}
                  >

                    {/* User question */}

                    <div>

                      <strong>
                        You
                      </strong>


                      <p>
                        {chat.question}
                      </p>

                    </div>


                    {/* AI answer */}

                    <div>

                      <strong>
                        AI
                      </strong>


                      <ReactMarkdown>
                        {chat.answer}
                      </ReactMarkdown>

                    </div>


                    {/* Sources */}

                    {chat.sources.length > 0 && (

                      <div>

                        <h3>
                          Sources
                        </h3>


                        {chat.sources.map(
                          (source) => (

                            <div
                              key={
                                source.chunk_id
                              }
                            >

                              <button
                                type="button"
                                onClick={() =>
                                  openSource(
                                    source
                                  )
                                }
                              >

                                📌{" "}
                                {
                                  source.file_path
                                }{" "}
                                | Lines{" "}
                                {
                                  source.start_line
                                }
                                -
                                {
                                  source.end_line
                                }

                              </button>

                            </div>

                          )
                        )}

                      </div>

                    )}


                    <hr />

                  </div>

                )
              )}

            </div>

          )}


          {/* =================================================
              SOURCE CODE VIEWER
              ================================================= */}

          {selectedSource && (

            <div
              id="source-viewer"
            >

              <hr />


              <h2>
                {selectedSource.file_path}
              </h2>


              <h3>

                Lines{" "}
                {selectedSource.start_line}
                -
                {selectedSource.end_line}

              </h3>


              {selectedSourceCode.length > 0 ? (

                <pre
                  style={{
                    textAlign:
                      "left",
                    overflowX:
                      "auto",
                    padding:
                      "20px",
                    lineHeight:
                      "1.6"
                  }}
                >

                  {selectedSourceCode.map(
                    (line) => (

                      <div
                        key={
                          line.number
                        }
                      >

                        <span
                          style={{
                            display:
                              "inline-block",
                            width:
                              "50px",
                            userSelect:
                              "none"
                          }}
                        >
                          {line.number}
                        </span>


                        <span>
                          {line.content}
                        </span>

                      </div>

                    )
                  )}

                </pre>

              ) : (

                <p>
                  Could not find the
                  source code in the
                  loaded files.
                </p>

              )}


              <button
                type="button"
                onClick={() =>
                  setSelectedSource(
                    null
                  )
                }
              >
                Close Source
              </button>

            </div>

          )}

        </section>

      )}

    </div>
  );
}


export default App;