# CV Processing Pipeline

Enterprise-oriented AI pipeline for automated CV ingestion, extraction, validation, normalization, and PostgreSQL persistence.

---

## Table of Contents

- [Overview](#overview)
- [Objectives](#objectives)
- [Architecture](#architecture)
- [Installation](#installation)



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

---
# installation
Python 3.11+
PostgreSQL
Git
Ollama (optional fallback provider) 

# Objectives

The main objectives of the project are:

- Automate CV document processing.
- Extract structured information from unstructured CVs.
- Process multiple CVs through a single API request.
- Process each CV independently.
- Prevent one failed CV from stopping the entire batch.
- Validate LLM-generated information before persistence.
- Separate extraction, validation, normalization, mapping, and persistence.
- Store structured CV information in PostgreSQL.

---

# Architecture

```text
                         +----------------------+
                         |        Client        |
                         |   Swagger / Postman  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |       FastAPI        |
                         |      API Layer       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |  Processing Service  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |       Docling        |
                         |  PDF / DOCX Parsing  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   Cleaned Markdown   |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |    LLM Extraction    |
                         | OpenRouter / Ollama  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |  Structured JSON     |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Pydantic Validation  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |     Normalizer       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |      DB Mapper       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |     Repository       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |     PostgreSQL       |
                         +----------------------+
                        
