from typing import Any

import structlog
from langchain_core.runnables import RunnableConfig

from zennode.core.models import (
    MasterySheetModel,
    QuizQuestionModel,
    RealityCheckModel,
    StudyState,
)
from zennode.infrastructure.audio import GroqWhisperService
from zennode.infrastructure.llm import (
    GeminiSynthesizerService,
    GroqSynthesizerService,
    OpenRouterVisionService,
)
from zennode.infrastructure.obsidian import ObsidianConnector
from zennode.prompts.system_prompts import (
    AUDIT_CRITIQUE_PROMPT,
    MASTERY_SYNTHESIS_PROMPT,
    QUIZ_GENERATION_PROMPT,
    REALITY_CHECK_PROMPT,
)

logger = structlog.get_logger(__name__)

def ingest_node(state: StudyState, config: RunnableConfig) -> dict[str, Any]:
    """Reads the exact dump file, loads raw text and parses out image/audio bytes."""
    import os
    dump_dir = state.get("dump_dir")
    
    if dump_dir and os.path.exists(dump_dir):
        logger.info("ingest_node_started_from_dump_dir", path=dump_dir)
        raw_text = ""
        raw_images = []
        audio_path = None
        
        txt_path = os.path.join(dump_dir, "clipboard.txt")
        if os.path.exists(txt_path):
            with open(txt_path, encoding="utf-8") as f:
                raw_text = f.read()
                
        img_path = os.path.join(dump_dir, "clipboard_image.png")
        if os.path.exists(img_path):
            raw_images.append(img_path)
                
        # Support audio
        wav_path = os.path.join(dump_dir, "audio.wav")
        if os.path.exists(wav_path):
            audio_path = wav_path
            
        return {
            "raw_text_context": raw_text,
            "raw_images": raw_images,
            "audio_file_path": audio_path
        }
    
    # Fallback to direct Obsidian parsing if no dump_dir provided
    logger.info("ingest_node_started", file=state["obsidian_file_path"])
    storage_provider = ObsidianConnector()
    raw_text, raw_images, embedded_audio = storage_provider.read_dump_context(state["obsidian_file_path"])
    
    result: dict[str, Any] = {
        "raw_text_context": raw_text,
        "raw_images": raw_images
    }
    
    # Auto-Audio Magic: If the user didn't explicitly pass an --audio flag in CLI, but we found an embedded voice note, use it!
    if embedded_audio and not state.get("audio_file_path"):
        result["audio_file_path"] = embedded_audio
        logger.info("ingest_node_auto_audio_detected", path=embedded_audio)
        
    return result

def transcribe_node(state: StudyState, config: RunnableConfig) -> dict[str, Any]:
    """Transcribes the audio file via Groq Whisper if provided and valid."""
    import os
    audio_path = state.get("audio_file_path")
    if not audio_path:
        logger.info("transcribe_node_skipped", reason="no_audio_file")
        return {"transcription": "No audio explanation provided. Relying solely on text/image context."}
        
    if os.path.exists(audio_path) and os.path.getsize(audio_path) < 100:
        logger.warning("transcribe_node_skipped", reason="audio_file_too_small_likely_empty", size=os.path.getsize(audio_path))
        return {"transcription": "Audio recording failed or was empty (likely due to missing microphone permissions or instant stop). Relying solely on text/image context."}
    
    logger.info("transcribe_node_started")
    whisper_service = GroqWhisperService()
    transcription = whisper_service.transcribe(audio_path)
    return {"transcription": transcription}

def reality_check_node(state: StudyState, config: RunnableConfig) -> dict[str, Any]:
    """Cross-examines the user's transcription against GenAI first-principles."""
    logger.info("reality_check_node_started")
    prompt = REALITY_CHECK_PROMPT.format(
        raw_text_context=state['raw_text_context'],
        transcription=state['transcription']
    )
    
    openrouter_vision_service = OpenRouterVisionService(model_name="openai/gpt-4o-mini")
    result = openrouter_vision_service.generate_structured_output(
        prompt=prompt, 
        images=state["raw_images"], 
        output_schema=RealityCheckModel
    )
    return {"reality_check_results": result}

def mastery_synthesis_node(state: StudyState, config: RunnableConfig) -> dict[str, Any]:
    """Synthesizes the corrected mental model into the Mastery Sheet format."""
    logger.info("mastery_synthesis_node_started")
    
    reality = state["reality_check_results"]
    correction_text = reality.correction_explanation if reality else ""
    
    prompt = MASTERY_SYNTHESIS_PROMPT.format(
        raw_text_context=state['raw_text_context'],
        transcription=state['transcription'],
        correction_text=correction_text
    )
    
    try:
        groq_service = GroqSynthesizerService(model_name="llama-3.3-70b-versatile")
        result = groq_service.generate_structured_output(
            prompt=prompt, 
            images=[], 
            output_schema=MasterySheetModel
        )
    except Exception as e:
        logger.warning("groq_mastery_failed_falling_back_to_gemini", error=str(e))
        gemini_service = GeminiSynthesizerService()
        result = gemini_service.generate_structured_output(
            prompt=prompt, 
            images=[], 
            output_schema=MasterySheetModel
        )
        
    return {"mastery_sheet": result}

def quiz_generation_node(state: StudyState, config: RunnableConfig) -> dict[str, Any]:
    """Generates 3 mental-map flashcard questions based on the Mastery Sheet."""
    logger.info("quiz_generation_node_started")
    
    # We cheat slightly to get a List return type by wrapping it in a dummy model inline.
    from pydantic import BaseModel, Field
    class QuizList(BaseModel):
        questions: list[QuizQuestionModel] = Field(description="List of exactly 3 questions.")
        
    ms = state.get('mastery_sheet')
    topic = ms.topic_title if ms else 'Unknown'
        
    prompt = QUIZ_GENERATION_PROMPT.format(topic=topic)
    
    try:
        groq_service = GroqSynthesizerService(model_name="llama-3.3-70b-versatile")
        result = groq_service.generate_structured_output(
            prompt=prompt, 
            images=[], 
            output_schema=QuizList
        )
    except Exception as e:
        logger.warning("groq_quiz_failed_falling_back_to_gemini", error=str(e))
        gemini_service = GeminiSynthesizerService()
        result = gemini_service.generate_structured_output(
            prompt=prompt, 
            images=[], 
            output_schema=QuizList
        )
        
    return {"quiz_flashcards": result.questions}

def audit_critique_node(state: StudyState, config: RunnableConfig) -> dict[str, Any]:
    """An Impeccable-inspired Audit/Critique node to enforce the 2026 Black Box vs Glass Box rules."""
    logger.info("audit_critique_node_started")
    
    ms = state.get("mastery_sheet")
    if not ms:
        return {}
        
    sections_text = "\n".join([f"Title: {s.title}\nContent: {s.content}\n" for s in ms.dynamic_sections])
        
    prompt = AUDIT_CRITIQUE_PROMPT.format(
        topic_title=ms.topic_title,
        ai_lifecycle_map=ms.ai_lifecycle_map,
        sections_text=sections_text
    )
    
    try:
        groq_service = GroqSynthesizerService(model_name="llama-3.3-70b-versatile")
        result = groq_service.generate_structured_output(
            prompt=prompt, 
            images=[], 
            output_schema=MasterySheetModel
        )
    except Exception as e:
        logger.warning("groq_audit_failed_falling_back_to_gemini", error=str(e))
        gemini_service = GeminiSynthesizerService()
        result = gemini_service.generate_structured_output(
            prompt=prompt, 
            images=[], 
            output_schema=MasterySheetModel
        )
    
    return {"audited_mastery_sheet": result}

