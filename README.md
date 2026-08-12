# CV Processing Pipeline

Enterprise-oriented AI pipeline for automated CV ingestion, extraction, validation, normalization, and PostgreSQL persistence.

---

## Table of Contents

- [Overview](#overview)
- [Objectives](#objectives)
- [Architecture](#architecture)
- [Complete Processing Flow](#complete-processing-flow)
- [LLM Data Flow](#llm-data-flow)
- [Technologies](#technologies)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Configuration](#environment-configuration)
- [LLM Providers](#llm-providers)
- [Database](#database)
- [Database Architecture](#database-architecture)
- [API](#api)
- [Batch Upload](#batch-upload)
- [Processing 100 CVs](#processing-100-cvs)
- [CV Extraction Schema](#cv-extraction-schema)
- [Pydantic Validation](#pydantic-validation)
- [Normalization](#normalization)
- [ORM Mapping](#orm-mapping)
- [Repository Layer](#repository-layer)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Running the Project](#running-the-project)
- [Collaborator Setup](#collaborator-setup)
- [Git Workflow](#git-workflow)
- [Development Rules](#development-rules)
- [Troubleshooting](#troubleshooting)
- [Current Status](#current-status)
- [Future Improvements](#future-improvements)

---

# Overview

The **CV Processing Pipeline** is an enterprise-oriented Python/FastAPI backend designed to automatically process CV documents.

The system accepts **PDF and DOCX** CVs, extracts their content using **Docling**, converts the document into cleaned Markdown, sends the Markdown content to an LLM, validates the structured response with **Pydantic**, normalizes the extracted information, maps it to **SQLAlchemy ORM entities**, and finally persists the data in **PostgreSQL**.

The project supports:

- PDF and DOCX CV processing
- Batch upload of up to 100 CVs per request
- Independent processing of each CV
- OpenRouter as the primary LLM provider
- Ollama as the fallback LLM provider
- Structured JSON extraction
- Pydantic validation
- Semantic LLM retry
- Data normalization
- SQLAlchemy ORM mapping
- PostgreSQL persistence
- Per-CV error isolation

The main pipeline is:

```text
CV (PDF / DOCX)
       |
       v
    Docling
       |
       v
 Clean Markdown
       |
       v
 System Prompt + CV Markdown
       |
       v
      LLM
(OpenRouter → Ollama fallback)
       |
       v
 Structured JSON
       |
       v
 Pydantic Validation
       |
       v
   Normalization
       |
       v
    ORM Mapping
       |
       v
    Repository
       |
       v
   PostgreSQL