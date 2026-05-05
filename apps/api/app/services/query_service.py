from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, AsyncGenerator

import httpx

from app.core.config import Settings, get_settings
from app.domain.models import ChatTurn, SearchResult
from app.services.document_service import search_documents


class LLMProviderError(RuntimeError):
    pass


OFF_TOPIC_RESPONSE = (
    "I can only answer questions about the company, its services, portfolio, "
    "technologies, or how it may help with customer projects."
)

_CUSTOMER_COMPANY_QUERY_TERMS = {
    "about",
    "app",
    "application",
    "automation",
    "booking",
    "build",
    "business",
    "case",
    "client",
    "clients",
    "company",
    "contact",
    "cost",
    "customer",
    "experience",
    "help",
    "offer",
    "offers",
    "platform",
    "portfolio",
    "price",
    "pricing",
    "product",
    "products",
    "project",
    "projects",
    "service",
    "services",
    "serve",
    "serves",
    "solution",
    "solutions",
    "specialise",
    "specialize",
    "team",
    "technologies",
    "technology",
    "timeline",
    "user",
    "users",
    "website",
}

_CUSTOMER_COMPANY_QUERY_PHRASES = (
    "what do you do",
    "who are you",
    "get started",
    "work with you",
    "your company",
    "your services",
    "your portfolio",
    "your team",
)


class OllamaGenerateProvider:
    def __init__(self, url: str, model: str, timeout_seconds: float = 30.0) -> None:
        self._url = url
        self._model = model
        self._timeout_seconds = timeout_seconds

    def generate(
        self,
        prompt: str,
        context: Sequence[SearchResult],
        history: Sequence[ChatTurn],
    ) -> str:
        try:
            response = httpx.post(
                self._url,
                json={"model": self._model, "prompt": prompt, "stream": False},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError("LLM provider failed") from exc

        answer = _extract_answer(response.json())
        if not answer.strip():
            raise LLMProviderError("LLM provider returned an empty answer")
        return answer

    async def generate_stream(
        self,
        prompt: str,
        context: Sequence[SearchResult],
        history: Sequence[ChatTurn],
    ) -> AsyncGenerator[str, None]:
        try:
            
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    self._url,
                    json={"model": self._model, "prompt": prompt, "stream": True},
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            if token := chunk.get("response"):
                                yield token
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            raise LLMProviderError(f"Streaming failed: {str(exc)}")


def get_chat_provider(settings: Settings | None = None) -> OllamaGenerateProvider:
    resolved_settings = settings or get_settings()
    if not resolved_settings.ollama_url or not resolved_settings.model_name:
        raise LLMProviderError("LLM provider is not configured")
    return OllamaGenerateProvider(
        url=resolved_settings.ollama_url,
        model=resolved_settings.model_name,
        timeout_seconds=resolved_settings.llm_timeout_seconds,
    )


def run_rag_query(query: str, top_k: int) -> tuple[str, list[str]]:
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Query cannot be empty")
    if not is_customer_company_query(normalized_query):
        return OFF_TOPIC_RESPONSE, []
    
    results = search_documents(normalized_query, top_k=top_k)
    prompt = build_rag_prompt(normalized_query, results)
    try:
        answer = get_chat_provider().generate(prompt, results, [])
    except LLMProviderError:
        raise
    except Exception as exc:
        raise LLMProviderError("LLM provider failed") from exc
    return answer, _sources(results)


async def run_rag_query_stream(query: str, top_k: int) -> AsyncGenerator[str, None]:
    
    try:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Query cannot be empty")
        if not is_customer_company_query(normalized_query):
            yield OFF_TOPIC_RESPONSE
            return

        
        results = search_documents(normalized_query, top_k=top_k)
        
        prompt = build_rag_prompt(normalized_query, results)
        
        
        provider = get_chat_provider()
        async for chunk in provider.generate_stream(prompt, results, []):
            yield chunk
            
    except Exception as e:
        
        print(f"BACKEND STREAM ERROR: {str(e)}")
        yield f"Error: {str(e)}"


def build_rag_prompt(query: str, results: Sequence[SearchResult]) -> str:
    context = "\n\n".join(
        f"Source {index + 1} ({_source(result)}):\n{result.text}"
        for index, result in enumerate(results)
    )
    if not context:
        context = "No retrieved context."
    return (
        "You are a customer-facing company assistant for the website frontend. "
        "Use a helpful, cheerful, and professional tone. "
        "Only answer customer questions about the company, its services, portfolio, "
        "technologies, or how the company may help with customer projects. "
        "If a question is unrelated to the company, politely say you can only answer "
        "questions about the company and its customer-facing work. "
        "Answer questions about the company and, when a user asks about a project, "
        "explain how the company may help with their project based only on the retrieved context. "
        "Answer the question using only the retrieved context and stay within the retrieved context. "
        "Do not invent services, experience, prices, timelines, guarantees, or contact details. "
        "If the answer requires counting items explicitly listed in the context, count them. "
        "If the context does not contain the answer, say you do not know and invite the user "
        "to share more project details or contact the company through the available website channels. "
        "Keep the response concise, clear, and customer-ready.\n\n"
        f"Retrieved context:\n{context}\n\n"
        f"Question:\n{query}\n\n"
        "Answer:"
    )


def is_customer_company_query(query: str) -> bool:
    normalized = query.lower()
    if any(phrase in normalized for phrase in _CUSTOMER_COMPANY_QUERY_PHRASES):
        return True

    words = {
        word.strip(".,!?;:()[]{}\"'")
        for word in normalized.replace("/", " ").replace("-", " ").split()
    }
    return bool(words & _CUSTOMER_COMPANY_QUERY_TERMS)


def _extract_answer(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("response"), str):
        return payload["response"]
    if isinstance(payload.get("answer"), str):
        return payload["answer"]
    
    message = payload.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]

    raise LLMProviderError("LLM provider returned an invalid response")


def _sources(results: Sequence[SearchResult]) -> list[str]:
    return [_source(result) for result in results]


def _source(result: SearchResult) -> str:
    return f"{result.metadata.get('source_name', 'document')}#{result.metadata.get('chunk_index', 0)}"
