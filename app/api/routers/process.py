"""
Process router.

Thin HTTP adapter: takes a cv_id (from a prior POST /upload), delegates
entirely to CVProcessingService, returns the LLM-extracted CV data. No
LLM, prompt, or provider logic lives here - see
services/cv_processing_service.py and llm/chains/cv_extraction_chain.py.
"""

import logging

from fastapi import APIRouter

from app.api.dependencies import CVProcessingServiceDep
from app.schemas.api_models import ProcessResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["process"])


@router.post("/process/{cv_id}", response_model=ProcessResponse)
async def process_cv(cv_id: str, service: CVProcessingServiceDep) -> ProcessResponse:
    """
    Run LLM extraction on a previously uploaded CV.

    Reads the cleaned Markdown saved during POST /upload (identified by
    cv_id) and runs it through the extraction chain: prompt -> LLM
    (OpenRouter or Ollama, whichever is configured as primary, with
    automatic fallback to the other) -> output parsing and schema
    validation, with semantic retries if the LLM's output is malformed.

    Returns the structured CV data matching the CVExtraction schema.
    """
    logger.info("Received process request for cv_id=%s", cv_id)
    extraction = service.process_cv_extraction(cv_id)
    return ProcessResponse(cv_id=cv_id, extraction=extraction)