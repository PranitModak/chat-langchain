"use client";

import { parsePartialJson } from "@langchain/core/output_parsers";
import {
  createContext,
  Dispatch,
  ReactNode,
  SetStateAction,
  useContext,
  useState,
} from "react";
import { AIMessage, BaseMessage, HumanMessage } from "@langchain/core/messages";
import { useToast } from "../hooks/use-toast";
import { v4 as uuidv4 } from "uuid";

import { useThreads } from "../hooks/useThreads";
import { ModelOptions } from "../types";
import { useRuns } from "../hooks/useRuns";
import { useUser } from "../hooks/useUser";
import { addDocumentLinks, createClient, nodeToStep, sendChat } from "./utils";
import { Thread } from "@langchain/langgraph-sdk";
import { useQueryState } from "nuqs";

interface GraphData {
  runId: string;
  isStreaming: boolean;
  messages: BaseMessage[];
  selectedModel: ModelOptions;
  setSelectedModel: Dispatch<SetStateAction<ModelOptions>>;
  setMessages: Dispatch<SetStateAction<BaseMessage[]>>;
  streamMessage: (currentThreadId: string, params: GraphInput) => Promise<void>;
  switchSelectedThread: (thread: Thread) => void;
}

type UserDataContextType = ReturnType<typeof useUser>;

type ThreadsDataContextType = ReturnType<typeof useThreads>;

type GraphContentType = {
  graphData: GraphData;
  userData: UserDataContextType;
  threadsData: ThreadsDataContextType;
};

const GraphContext = createContext<GraphContentType | undefined>(undefined);

export interface GraphInput {
  messages?: Record<string, any>[];
}

export function GraphProvider({ children }: { children: ReactNode }) {
  const { userId } = useUser();
  const {
    isUserThreadsLoading,
    userThreads,
    getThreadById,
    setUserThreads,
    getUserThreads,
    createThread,
    deleteThread,
  } = useThreads(userId);
  const [runId, setRunId] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const { toast } = useToast();
  const { shareRun } = useRuns();
  const [messages, setMessages] = useState<BaseMessage[]>([]);
  const [selectedModel, setSelectedModel] = useState<ModelOptions>(
    "google_genai/gemini-2.5-pro",
  );
  const [_threadId, setThreadId] = useQueryState("threadId");

  const streamMessage = async (
    currentThreadId: string,
    params: GraphInput,
  ): Promise<void> => {
    if (!userId) {
      toast({
        title: "Error",
        description: "User ID not found",
      });
      return;
    }

    setRunId("");
    setIsStreaming(true);
    try {
      const response = await sendChat(params.messages ?? [], selectedModel);
      setMessages((prevMessages) => [
        ...prevMessages,
        new AIMessage({ content: response.answer || response, id: uuidv4() }),
      ]);
    } catch (e) {
      toast({
        title: "Error",
        description: "Failed to get response from backend.",
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const switchSelectedThread = (thread: Thread) => {
    setThreadId(thread.thread_id);
    if (!thread.values) {
      setMessages([]);
      return;
    }
    const threadValues = thread.values as Record<string, any>;

    const actualMessages = (
      threadValues.messages as Record<string, any>[]
    ).flatMap((msg, index, array) => {
      if (msg.type === "human") {
        // insert progress bar afterwards
        const progressAIMessage = new AIMessage({
          id: uuidv4(),
          content: "",
          tool_calls: [
            {
              name: "progress",
              args: {
                step: 4, // Set to done.
              },
            },
          ],
        });
        return [
          new HumanMessage({
            ...msg,
            content: msg.content,
          }),
          progressAIMessage,
        ];
      }

      if (msg.type === "ai") {
        const isLastAiMessage =
          index === array.length - 1 || array[index + 1].type === "human";
        if (isLastAiMessage) {
          const routerMessage = threadValues.router
            ? new AIMessage({
                content: "",
                id: uuidv4(),
                tool_calls: [
                  {
                    name: "router_logic",
                    args: threadValues.router,
                  },
                ],
              })
            : undefined;
          const selectedDocumentsAIMessage = threadValues.documents?.length
            ? new AIMessage({
                content: "",
                id: uuidv4(),
                tool_calls: [
                  {
                    name: "selected_documents",
                    args: {
                      documents: threadValues.documents,
                    },
                  },
                ],
              })
            : undefined;
          const answerHeaderToolMsg = new AIMessage({
            content: "",
            tool_calls: [
              {
                name: "answer_header",
                args: {},
              },
            ],
          });
          return [
            ...(routerMessage ? [routerMessage] : []),
            ...(selectedDocumentsAIMessage ? [selectedDocumentsAIMessage] : []),
            answerHeaderToolMsg,
            new AIMessage({
              ...msg,
              content: msg.content,
            }),
          ];
        }
        return new AIMessage({
          ...msg,
          content: msg.content,
        });
      }

      return []; // Return an empty array for any other message types
    });

    setMessages(actualMessages);
  };

  const contextValue: GraphContentType = {
    userData: {
      userId,
    },
    threadsData: {
      isUserThreadsLoading,
      userThreads,
      getThreadById,
      setUserThreads,
      getUserThreads,
      createThread,
      deleteThread,
    },
    graphData: {
      runId,
      isStreaming,
      messages,
      selectedModel,
      setSelectedModel,
      setMessages,
      streamMessage,
      switchSelectedThread,
    },
  };

  return (
    <GraphContext.Provider value={contextValue}>
      {children}
    </GraphContext.Provider>
  );
}

export function useGraphContext() {
  const context = useContext(GraphContext);
  if (context === undefined) {
    throw new Error("useGraphContext must be used within a GraphProvider");
  }
  return context;
}
