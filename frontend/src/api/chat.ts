export async function askQuestion(
  projectId: number,
  question: string,
  conversationHistory: {
    role: "user" | "assistant";
    content: string;
  }[] = []
) {
  const response = await fetch(
    `http://127.0.0.1:8000/chat/project/${projectId}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: question,
        top_k: 3,
        conversation_history: conversationHistory,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to get answer");
  }

  return response.json();
}