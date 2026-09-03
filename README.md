# Chatbot LangGraph Workspace

This repository is structured as a monorepo containing a FastAPI/LangGraph backend and a Next.js frontend:

- **[`backend/`](./backend)**: FastAPI + LangGraph chatbot backend with PostgreSQL persistence, JWT authentication, and Multi-Server MCP client.
- **[`frontend/`](./frontend)**: Next.js chatbot interface designed with a Gemini-style web UI.

Please refer to the README files in their respective folders for detailed documentation, setup, and run instructions.
- **Multi-file uploads**: Completed! `pending_upload` supports concurrent multi-file ingestion with dynamic filename matching.