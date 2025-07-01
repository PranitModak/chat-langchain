import { Client } from "@langchain/langgraph-sdk";

export function createClient() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3000/api";
  return new Client({
    apiUrl,
  });
}

export function nodeToStep(node: string) {
  switch (node) {
    case "analyze_and_route_query":
      return 0;
    case "create_research_plan":
      return 1;
    case "conduct_research":
      return 2;
    case "respond":
      return 3;
    default:
      return 0;
  }
}

export function addDocumentLinks(
  text: string,
  inputDocuments: Record<string, any>[],
): string {
  return text.replace(/\[(\d+)\]/g, (match, number) => {
    const index = parseInt(number, 10);
    if (index >= 0 && index < inputDocuments.length) {
      const document = inputDocuments[index];
      if (document && document.metadata && document.metadata.source) {
        return `[[${number}]](${document.metadata.source})`;
      }
    }
    // Return the original match if no corresponding document is found
    return match;
  });
}

export async function sendChat(messages: any[], model: string) {
  const response = await fetch("http://localhost:8080/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, model }),
  });
  if (!response.ok) throw new Error("Chat API error");
  return response.json();
}
