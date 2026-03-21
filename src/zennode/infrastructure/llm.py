from typing import Any, TypeVar, cast

import structlog
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, SecretStr
from tenacity import retry, stop_after_attempt, wait_exponential

from zennode.infrastructure.config import Config

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

class GeminiSynthesizerService:
    def __init__(self, model_name: str = "gemini-2.0-flash") -> None:
        self.model_name = model_name
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=0.0, # Deterministic outputs for structured data
            google_api_key=Config.get_gemini_api_key(),
            max_retries=3
        )

    @retry(wait=wait_exponential(min=2, max=15), stop=stop_after_attempt(4), reraise=True)
    def generate_structured_output(
        self, 
        prompt: str, 
        images: list[str], 
        output_schema: type[T]
    ) -> T:
        """Generates a strictly typed Pydantic object from multi-modal input."""
        logger.info("gemini_generation_started", schema=output_schema.__name__, model=self.model_name)
        
        # Bind the Pydantic schema to the LLM
        structured_llm = self.llm.with_structured_output(output_schema)
        
        # Prepare content blocks
        content: list[dict[str, Any] | str] = [{"type": "text", "text": prompt}]
        for img_path in images:
            try:
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
                import base64
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                content.append({
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{img_b64}"
                })
            except Exception as e:
                logger.error("gemini_image_load_failed", path=img_path, error=str(e))
            
        message = HumanMessage(content=content)
        
        try:
            result = structured_llm.invoke([message])
            logger.info("gemini_generation_success", schema=output_schema.__name__)
            return cast(T, result)
        except Exception as e:
            logger.error("gemini_generation_failed", error=str(e), schema=output_schema.__name__)
            raise

class GroqSynthesizerService:
    def __init__(self, model_name: str = "llama-3.3-70b-versatile") -> None:
        self.model_name = model_name
        self.llm = ChatGroq(
            model=self.model_name,
            temperature=0.0,
            api_key=SecretStr(Config.get_groq_api_key()),
            max_retries=3
        )

    @retry(wait=wait_exponential(min=2, max=15), stop=stop_after_attempt(4), reraise=True)
    def generate_structured_output(
        self, 
        prompt: str, 
        images: list[str], 
        output_schema: type[T]
    ) -> T:
        """Generates a strictly typed Pydantic object from text input using Groq's blinding-fast Llama models."""
        logger.info("groq_generation_started", schema=output_schema.__name__, model=self.model_name)
        
        structured_llm = self.llm.with_structured_output(output_schema)
        message = HumanMessage(content=prompt)
        
        try:
            result = structured_llm.invoke([message])
            logger.info("groq_generation_success", schema=output_schema.__name__)
            return cast(T, result)
        except Exception as e:
            logger.error("groq_generation_failed", error=str(e), schema=output_schema.__name__)
            raise

class OpenRouterVisionService:
    def __init__(self, model_name: str = "google/gemini-2.0-flash:free") -> None:
        self.model_name = model_name
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.0,
            api_key=SecretStr(Config.get_openrouter_api_key()),
            base_url="https://openrouter.ai/api/v1",
            max_retries=3
        )

    @retry(wait=wait_exponential(min=2, max=15), stop=stop_after_attempt(4), reraise=True)
    def generate_structured_output(
        self, 
        prompt: str, 
        images: list[str], 
        output_schema: type[T]
    ) -> T:
        """Generates a strictly typed Pydantic object from text/image input using OpenRouter."""
        logger.info("openrouter_generation_started", schema=output_schema.__name__, model=self.model_name)
        
        structured_llm = self.llm.with_structured_output(output_schema)
        
        if images:
            content: list[dict[str, Any] | str] = [{"type": "text", "text": prompt}]
            for img_path in images:
                try:
                    with open(img_path, "rb") as f:
                        img_bytes = f.read()
                    import base64
                    b64 = base64.b64encode(img_bytes).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    })
                except Exception as e:
                    logger.error("openrouter_image_load_failed", path=img_path, error=str(e))
            message = HumanMessage(content=content)
        else:
            message = HumanMessage(content=prompt)
        
        try:
            result = structured_llm.invoke([message])
            logger.info("openrouter_generation_success", schema=output_schema.__name__)
            return cast(T, result)
        except Exception as e:
            logger.error("openrouter_generation_failed", error=str(e), schema=output_schema.__name__)
            raise
