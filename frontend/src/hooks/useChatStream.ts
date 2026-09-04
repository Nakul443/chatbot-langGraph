// This hook manages the streaming of chat messages from the server to the UI
// It handles the addition of user messages, streaming assistant responses, and error handling during the streaming process
// It ensures that the UI remains responsive and provides real-time feedback to the user during chat interactions

// the main job of this file is to handle the communication between your app and the backend server
// when a user sends a chat message, specifically managing real-time text streaming

import { useChatStore } from '@/store/authStore';
import { Message } from '@/types/chat';

// This hook provides a function to stream chat messages from the server, updating the UI in real-time as new tokens are received
export function useChatStream() {
  const { addMessage, updateLastMessage, setIsStreaming } = useChatStore();

  const streamChat = async (message: string, threadId: string, file?: File | null) => {
    setIsStreaming(true);

    // 1. Add user message to UI
    let displayMessage = message;
    if (file) {
      if (message.trim()) {
        displayMessage = `Uploaded \`${file.name}\` — ${message}`;
      } else {
        displayMessage = `Uploaded \`${file.name}\``;
      }
    }

    const userMsg: Message = {
      id: Math.random().toString(),
      role: 'user',
      content: displayMessage,
    };
    addMessage(userMsg);

    // 2. Add empty assistant bubble
    const assistantMsgId = Math.random().toString();
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
    };
    addMessage(assistantMsg);

    try {
      let response: Response;

      if (file) {
        const formData = new FormData();
        formData.append('files', file);
        formData.append('thread_id', threadId);
        if (message.trim()) {
          formData.append('message', message);
        }

        response = await fetch('/api/chat', {
          method: 'POST',
          body: formData,
        });
      } else {
        response = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message,
            thread_id: threadId,
          }),
        });
      }

      if (!response.ok) {
        let errorMessage = 'Streaming failed';
        try {
          const errData = await response.json();
          errorMessage = errData.error || errData.message || errorMessage;
        } catch {
          try {
            const text = await response.text();
            errorMessage = text || errorMessage;
          } catch {}
        }
        throw new Error(errorMessage);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No readable stream reader');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep the incomplete line in buffer

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith('data:')) {
            const dataStr = trimmed.slice(5).trim();

            if (dataStr === '[DONE]') {
              break;
            }

            try {
              // Parse JSON token update
              const parsed = JSON.parse(dataStr);
              // Handle standard server-sent token chunk formats
              const token = parsed.token || parsed.content || (typeof parsed === 'string' ? parsed : '');
              if (token) {
                updateLastMessage(token);
              }
            } catch {
              // If not JSON, it could be a raw text chunk
              updateLastMessage(dataStr);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error during streaming:', error);
      updateLastMessage('\n\n*(An error occurred while streaming the response)*');
    } finally {
      setIsStreaming(false);
    }
  };

  return { streamChat };
}
