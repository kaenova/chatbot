/**
 * Conversion utilities for transforming Langgraph state messages to Assistant UI format
 */

import type { CompleteAttachment } from "@assistant-ui/react";

// Assistant UI Types (based on the documentation)
export type TextMessagePart = {
  readonly type: "text";
  readonly text: string;
  readonly parentId?: string;
};

export type ReasoningMessagePart = {
  readonly type: "reasoning";
  readonly text: string;
  readonly parentId?: string;
};

export type SourceMessagePart = {
  readonly type: "source";
  readonly sourceType: "url";
  readonly id: string;
  readonly url: string;
  readonly title?: string;
  readonly parentId?: string;
};

export type ImageMessagePart = {
  readonly type: "image";
  readonly image: string;
  readonly filename?: string;
};

export type FileMessagePart = {
  readonly type: "file";
  readonly filename?: string;
  readonly data: string;
  readonly mimeType: string;
};

export type Unstable_AudioMessagePart = {
  readonly type: "audio";
  readonly audio: {
    readonly data: string;
    readonly format: "mp3" | "wav";
  };
};

export type ToolCallMessagePart<TArgs = Record<string, unknown>, TResult = unknown> = {
  readonly type: "tool-call";
  readonly toolCallId: string;
  readonly toolName: string;
  readonly args: TArgs;
  readonly result?: TResult | undefined;
  readonly isError?: boolean | undefined;
  readonly argsText: string;
  readonly artifact?: unknown;
  readonly parentId?: string;
};

export type ThreadUserMessagePart =
  | TextMessagePart
  | ImageMessagePart
  | FileMessagePart
  | Unstable_AudioMessagePart;

export type ThreadAssistantMessagePart =
  | TextMessagePart
  | ReasoningMessagePart
  | ToolCallMessagePart
  | SourceMessagePart
  | FileMessagePart
  | ImageMessagePart;

export type MessageStatus =
  | {
      readonly type: "running";
    }
  | {
      readonly type: "requires-action";
      readonly reason: "tool-calls";
    }
  | {
      readonly type: "complete";
      readonly reason: "stop" | "unknown";
    }
  | {
      readonly type: "incomplete";
      readonly reason:
        | "cancelled"
        | "tool-calls"
        | "length"
        | "content-filter"
        | "other"
        | "error";
      readonly error?: unknown;
    };

export type ThreadStep = {
  readonly messageId?: string;
  readonly usage?:
    | {
        readonly promptTokens: number;
        readonly completionTokens: number;
      }
    | undefined;
};

type MessageCommonProps = {
  readonly id: string;
  readonly createdAt: Date;
};

export type ThreadSystemMessage = MessageCommonProps & {
  readonly role: "system";
  readonly content: readonly [TextMessagePart];
  readonly metadata: {
    readonly custom: Record<string, unknown>;
  };
};

export type ThreadUserMessage = MessageCommonProps & {
  readonly role: "user";
  readonly content: readonly ThreadUserMessagePart[];
  readonly attachments: readonly CompleteAttachment[];
  readonly metadata: {
    readonly custom: Record<string, unknown>;
  };
};

export type ThreadAssistantMessage = MessageCommonProps & {
  readonly role: "assistant";
  readonly content: readonly ThreadAssistantMessagePart[];
  readonly status: MessageStatus;
  readonly metadata: {
    readonly unstable_state: unknown;
    readonly unstable_annotations: readonly unknown[];
    readonly unstable_data: readonly unknown[];
    readonly steps: readonly ThreadStep[];
    readonly custom: Record<string, unknown>;
  };
};

export type ThreadMessage = ThreadSystemMessage | ThreadUserMessage | ThreadAssistantMessage;

// Content type for message content that can be text or structured content blocks
export type MessageContent = string | Array<{
  type: string;
  text?: string;
  image_url?: { url: string };
  [key: string]: unknown;
}>;

// Tool call structure
export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  [key: string]: unknown;
}

// Langgraph Types (based on the JSON structure analysis)
export interface LangchainMessageBase {
  lc: number;
  type: "constructor";
  id: string[];
  kwargs: {
    content: MessageContent;
    type: string;
    id: string;
    [key: string]: unknown;
  };
}

export interface LangchainHumanMessage extends LangchainMessageBase {
  id: ["langchain", "schema", "messages", "HumanMessage"];
  kwargs: {
    content: MessageContent;
    type: "human";
    id: string;
  };
}

export interface LangchainAIMessage extends LangchainMessageBase {
  id: ["langchain", "schema", "messages", "AIMessage"];
  kwargs: {
    content: string;
    type: "ai";
    id: string;
    additional_kwargs?: Record<string, unknown>;
    response_metadata?: {
      token_usage?: {
        completion_tokens: number;
        prompt_tokens: number;
        total_tokens: number;
      };
      finish_reason?: string;
      model_name?: string;
      [key: string]: unknown;
    };
    usage_metadata?: {
      input_tokens: number;
      output_tokens: number;
      total_tokens: number;
    };
    tool_calls?: ToolCall[];
    invalid_tool_calls?: ToolCall[];
  };
}

export interface LangchainSystemMessage extends LangchainMessageBase {
  id: ["langchain", "schema", "messages", "SystemMessage"];
  kwargs: {
    content: string;
    type: "system";
    id: string;
  };
}

export interface LangchainToolMessage extends LangchainMessageBase {
  id: ["langchain", "schema", "messages", "ToolMessage"];
  kwargs: {
    content: string;
    type: "tool";
    id: string;
    name: string;
    tool_call_id: string;
    status?: "success" | "error";
  };
}

export type LangchainMessage = LangchainHumanMessage | LangchainAIMessage | LangchainSystemMessage | LangchainToolMessage;

export interface LanggraphStateCheckpoint {
  messages: LangchainMessage[];
  [key: string]: unknown;
}

export interface LanggraphStateHistoryEntry {
  0: LanggraphStateCheckpoint; // State data
  1: string[]; // Node names
  2: {
    configurable: {
      thread_id: string;
      checkpoint_ns: string;
      checkpoint_id: string;
    };
  }; // Config
  3: {
    source: string;
    step: number;
    parents: Record<string, unknown>;
  }; // Metadata
  4: string; // Timestamp
  5?: unknown; // Parent config
  6?: unknown[][]; // Tasks
  7?: unknown[]; // Pending writes
}

export type LanggraphStateHistory = LanggraphStateHistoryEntry[];

// Conversion Functions
export function convertLangchainMessageContent(content: MessageContent): ThreadUserMessagePart[] | ThreadAssistantMessagePart[] {
  if (typeof content === "string") {
    return [{
      type: "text" as const,
      text: content,
    }];
  }

  if (Array.isArray(content)) {

    // @ts-expect-error // TypeScript is not able to infer the type correctly here
    return content.map(item => {
      if (typeof item === "string") {
        return {
          type: "text" as const,
          text: item,
        };
      }
      
      if (typeof item === "object" && item.type === "text") {
        return {
          type: "text" as const,
          text: item.text || "",
        };
      }

      // Handle other content types (images, files, etc.)
      if (typeof item === "object" && item.type === "image_url") {
        if (item.image_url && item.image_url.url) {
          return {
            type: "image" as const,
            image: item.image_url.url,
          };
        }

        return {
          type: "image" as const,
          image: item.image_url || "",
        };
      }

      // Handle image in base64
      if (typeof item === "object" && item.type === "image" && item.source_type === "base64" && item.data && item.mime_type) {
          return {
            type: "image" as const,
            image: `data:${item.mime_type};base64,${item.data}`,
          }
      }

      if (typeof item === "object" && item.type === "image" && item.image) {
          return {
            type: "image" as const,
            image: item.image,
            text: item.text || undefined,
          }
      }

      // Fallback to text
      return {
        type: "text" as const,
        text: JSON.stringify(item),
      };
    });
  }

  return [{
    type: "text" as const,
    text: String(content),
  }];
}

export function extractLangchainMessageTextContent(content: MessageContent): TextMessagePart[] {
  if (typeof content === "string") {
    return [{
      type: "text" as const,
      text: content,
    }];
  }

  if (Array.isArray(content)) {
    const textParts: TextMessagePart[] = [];

    for (const item of content) {
      if (typeof item === "string") {
        textParts.push({
          type: "text" as const,
          text: item,
        });
      } else if (typeof item === "object" && item.type === "text" && typeof item.text === "string") {
        textParts.push({
          type: "text" as const,
          text: item.text,
        });
      }
      // Skip non-text items - they will be handled as attachments
    }

    return textParts;
  }

  return [{
    type: "text" as const,
    text: String(content),
  }];
}

export function extractLangchainMessageAttachments(content: MessageContent): CompleteAttachment[] {
  const attachments: CompleteAttachment[] = [];

  if (typeof content === "string") {
    // String content has no attachments
    return attachments;
  }

  if (Array.isArray(content)) {
    let attachmentIndex = 0;

    for (const item of content) {
      if (typeof item === "object" && item) {
        // Handle image_url type (from your example)
        if (item.type === "image_url" && item.image_url && typeof item.image_url === "object" && "url" in item.image_url && typeof item.image_url.url === "string") {
          const url = item.image_url.url;
          const isDataUrl = url.startsWith("data:");
          
          // Create image content for the attachment
          const imageContent: ThreadUserMessagePart[] = [{
            type: "image" as const,
            image: url,
          }];

          attachments.push({
            id: `attachment-${attachmentIndex++}`,
            type: "image" as const,
            name: `image-${attachmentIndex}.png`,
            contentType: isDataUrl ? url.split(";")[0].substring(5) : "image/png",
            status: { type: "complete" as const },
            content: imageContent,
          });
        }
        // Handle direct image type with base64
        else if (item.type === "image" && "source_type" in item && item.source_type === "base64" && "data" in item && typeof item.data === "string" && "mime_type" in item && typeof item.mime_type === "string") {
          const dataUrl = `data:${item.mime_type};base64,${item.data}`;
          
          const imageContent: ThreadUserMessagePart[] = [{
            type: "image" as const,
            image: dataUrl,
          }];

          attachments.push({
            id: `attachment-${attachmentIndex++}`,
            type: "image" as const,
            name: `image-${attachmentIndex}.${getFileExtensionFromMimeType(item.mime_type)}`,
            contentType: item.mime_type,
            status: { type: "complete" as const },
            content: imageContent,
          });
        }
        // Handle direct image type with url
        else if (item.type === "image" && "image" in item && typeof item.image === "string") {
          const imageUrl = item.image;
          const isDataUrl = imageUrl.startsWith("data:");
          
          const imageContent: ThreadUserMessagePart[] = [{
            type: "image" as const,
            image: imageUrl,
          }];

          attachments.push({
            id: `attachment-${attachmentIndex++}`,
            type: "image" as const,
            name: `image-${attachmentIndex}.png`,
            contentType: isDataUrl ? imageUrl.split(";")[0].substring(5) : "image/png",
            status: { type: "complete" as const },
            content: imageContent,
          });
        }
        // Handle file attachments (if they exist in the future)
        else if (item.type === "file" && "data" in item && typeof item.data === "string" && "mime_type" in item && typeof item.mime_type === "string") {
          const filename = ("filename" in item && typeof item.filename === "string") 
            ? item.filename 
            : `file-${attachmentIndex}.${getFileExtensionFromMimeType(item.mime_type)}`;

          const fileContent: ThreadUserMessagePart[] = [{
            type: "file" as const,
            filename,
            data: item.data,
            mimeType: item.mime_type,
          }];

          attachments.push({
            id: `attachment-${attachmentIndex++}`,
            type: "file" as const,
            name: filename,
            contentType: item.mime_type,
            status: { type: "complete" as const },
            content: fileContent,
          });
        }
      }
    }
  }

  return attachments;
}

// Helper function to get file extension from MIME type
function getFileExtensionFromMimeType(mimeType: string): string {
  const mimeToExtension: Record<string, string> = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "text/plain": "txt",
    "application/pdf": "pdf",
    "application/json": "json",
    "application/xml": "xml",
    "text/html": "html",
    "text/css": "css",
    "text/javascript": "js",
    "application/javascript": "js",
  };

  return mimeToExtension[mimeType] || "bin";
}

export function convertLangchainToolCalls(
  toolCalls: ToolCall[], 
  toolResults?: Map<string, { result: string; isError: boolean }>
): ToolCallMessagePart[] {
  if (!Array.isArray(toolCalls) || toolCalls.length === 0) {
    return [];
  }

  return toolCalls.map(toolCall => {
    const toolCallId = toolCall.id || "";
    const toolResult = toolResults?.get(toolCallId);
    
    return {
      type: "tool-call" as const,
      toolCallId,
      toolName: toolCall.name || "unknown",
      args: toolCall.args || {},
      argsText: JSON.stringify(toolCall.args || {}),
      result: toolResult?.result,
      isError: toolResult?.isError || false,
    };
  });
}

export function convertLangchainMessageToThreadMessage(
  langchainMsg: LangchainMessage,
  checkpoint: LanggraphStateCheckpoint,
  timestamp: string,
  toolResults?: Map<string, { result: string; isError: boolean }>
): ThreadMessage {
  const createdAt = new Date(timestamp);
  const messageId = langchainMsg.kwargs.id;

  // Convert based on message type
  if (langchainMsg.id[3] === "HumanMessage") {
    const textContent = extractLangchainMessageTextContent(langchainMsg.kwargs.content);
    const attachments = extractLangchainMessageAttachments(langchainMsg.kwargs.content);
    
    return {
      id: messageId,
      role: "user" as const,
      createdAt,
      content: textContent,
      attachments,
      metadata: {
        custom: {},
      },
    };
  }

  if (langchainMsg.id[3] === "AIMessage") {
    const aiMsg = langchainMsg as LangchainAIMessage;
    const textContent = convertLangchainMessageContent(aiMsg.kwargs.content) as ThreadAssistantMessagePart[];
    const toolCalls = convertLangchainToolCalls(aiMsg.kwargs.tool_calls || [], toolResults);
    
    const content = [...textContent, ...toolCalls];

    // Determine status based on finish_reason and tool_calls
    let status: MessageStatus;
    const finishReason = aiMsg.kwargs.response_metadata?.finish_reason;
    const hasToolCalls = toolCalls.length > 0;

    if (hasToolCalls && finishReason !== "stop") {
      status = {
        type: "requires-action" as const,
        reason: "tool-calls" as const,
      };
    } else if (finishReason === "stop") {
      status = {
        type: "complete" as const,
        reason: "stop" as const,
      };
    } else {
      status = {
        type: "complete" as const,
        reason: "unknown" as const,
      };
    }

    // Create steps from usage metadata
    const steps: ThreadStep[] = [];
    if (aiMsg.kwargs.usage_metadata || aiMsg.kwargs.response_metadata?.token_usage) {
      const usageMetadata = aiMsg.kwargs.usage_metadata;
      const tokenUsage = aiMsg.kwargs.response_metadata?.token_usage;
      
      if (usageMetadata) {
        steps.push({
          messageId,
          usage: {
            promptTokens: usageMetadata.input_tokens || 0,
            completionTokens: usageMetadata.output_tokens || 0,
          },
        });
      } else if (tokenUsage) {
        steps.push({
          messageId,
          usage: {
            promptTokens: tokenUsage.prompt_tokens || 0,
            completionTokens: tokenUsage.completion_tokens || 0,
          },
        });
      }
    }

    return {
      id: messageId,
      role: "assistant" as const,
      createdAt,
      content,
      status,
      metadata: {
        unstable_state: aiMsg.kwargs.response_metadata || {},
        unstable_annotations: [],
        unstable_data: [],
        steps,
        custom: {},
      },
    };
  }

  if (langchainMsg.id[3] === "SystemMessage") {
    const content: [TextMessagePart] = [{
      type: "text" as const,
      text: String(langchainMsg.kwargs.content),
    }];

    return {
      id: messageId,
      role: "system" as const,
      createdAt,
      content,
      metadata: {
        custom: {},
      },
    };
  }

  // Fallback - treat as user message
  const content = convertLangchainMessageContent(langchainMsg.kwargs.content) as ThreadUserMessagePart[];
  return {
    id: messageId,
    role: "user" as const,
    createdAt,
    content,
    attachments: [],
    metadata: {
      custom: {},
    },
  };
}

export function buildMessageParentChildRelationships(
  messages: ThreadMessage[]
): Array<{ message: ThreadMessage; parentId: string | null }> {
  const messageWithParents: Array<{ message: ThreadMessage; parentId: string | null }> = [];
  
  // Simple linear parent-child relationship based on chronological order
  // The first message has no parent, each subsequent message's parent is the previous one
  for (let i = 0; i < messages.length; i++) {
    const parentId = i > 0 ? messages[i - 1].id : null;
    messageWithParents.push({
      message: messages[i],
      parentId,
    });
  }

  return messageWithParents;
}

export function processMessagesWithToolResults(
  messages: LangchainMessage[]
): { processedMessages: LangchainMessage[]; toolResults: Map<string, { result: string; isError: boolean }> } {
  const toolResults = new Map<string, { result: string; isError: boolean }>();
  const processedMessages: LangchainMessage[] = [];

  // First pass: collect all tool results
  for (const message of messages) {
    if (message.id[3] === "ToolMessage") {
      const toolMsg = message as LangchainToolMessage;
      const toolCallId = toolMsg.kwargs.tool_call_id;
      const result = toolMsg.kwargs.content;
      const isError = toolMsg.kwargs.status === "error";
      
      toolResults.set(toolCallId, { result, isError });
    }
  }

  // Second pass: filter out ToolMessages (they'll be incorporated into AIMessages)
  for (const message of messages) {
    if (message.id[3] !== "ToolMessage") {
      processedMessages.push(message);
    }
  }

  return { processedMessages, toolResults };
}

export function convertLanggraphStateToAssistantUI(
  stateHistory: LanggraphStateHistory
): Array<{ message: ThreadMessage; parentId: string | null }> {
  if (!Array.isArray(stateHistory) || stateHistory.length === 0) {
    return [];
  }

  // Get the latest state (first entry in the array)
  const latestState = stateHistory[0];
  if (!latestState || !latestState[0] || !latestState[0].messages) {
    return [];
  }

  const checkpoint = latestState[0];
  const timestamp = latestState[4];
  
  // Process messages to extract tool results and filter out ToolMessages
  const { processedMessages, toolResults } = processMessagesWithToolResults(checkpoint.messages);
  
  // Convert all messages from the latest state
  const threadMessages: ThreadMessage[] = processedMessages.map(langchainMsg =>
    convertLangchainMessageToThreadMessage(langchainMsg, checkpoint, timestamp, toolResults)
  );

  // Build parent-child relationships
  return buildMessageParentChildRelationships(threadMessages);
}

// Utility function to extract conversation history from multiple checkpoints
export function loadFromLanggraphStateHistoryJSON(
  stateHistory: LanggraphStateHistory
): Array<{ message: ThreadMessage; parentId: string | null }> {
  if (!Array.isArray(stateHistory) || stateHistory.length === 0) {
    return [];
  }

  // Collect all unique messages across all checkpoints
  const allMessages = new Map<string, { message: ThreadMessage; timestamp: string }>();

  for (const entry of stateHistory) {
    if (!entry[0] || !entry[0].messages) continue;
    
    const checkpoint = entry[0];
    const timestamp = entry[4];
    
    // Process messages to extract tool results and filter out ToolMessages
    const { processedMessages, toolResults } = processMessagesWithToolResults(checkpoint.messages);
    
    for (const langchainMsg of processedMessages) {
      const messageId = langchainMsg.kwargs.id;
      
      // Only add if we haven't seen this message ID before
      if (!allMessages.has(messageId)) {
        const threadMessage = convertLangchainMessageToThreadMessage(
          langchainMsg,
          checkpoint,
          timestamp,
          toolResults
        );
        allMessages.set(messageId, { message: threadMessage, timestamp });
      }
    }
  }

  // Sort messages by creation time and build relationships
  const sortedMessages = Array.from(allMessages.values())
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map(item => item.message);

  return buildMessageParentChildRelationships(sortedMessages);
}
