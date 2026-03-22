from typing import Any

import structlog
from langchain_core.runnables import RunnableConfig

from zennode.core.models import (
    MasterySheetModel,
    QuizQuestionModel,
    RealityCheckModel,
    StudyState,
    ContextIntegrityModel,
)
from zennode.infrastructure.audio import GroqWhisperService
from zennode.infrastructure.llm import (
    GeminiSynthesizerService,
    GroqSynthesizerService,
    OpenRouterVisionService,
    LLMRouter,
)
from zennode.infrastructure.obsidian import ObsidianConnector
from zennode.prompts.system_prompts import (
    AUDIT_CRITIQUE_PROMPT,
    MASTERY_SYNTHESIS_PROMPT,
    QUIZ_GENERATION_PROMPT,
    REALITY_CHECK_PROMPT,
    CONTEXT_PRECHECK_PROMPT,
)
from zennode.infrastructure.pii import PIIMasker

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
                
        # Support audio (V2 Optimization: compressed m4a files)
        wav_path = os.path.join(dump_dir, "audio.wav")
        m4a_path = os.path.join(dump_dir, "audio.m4a")
        if os.path.exists(m4a_path):
            audio_path = m4a_path
        elif os.path.exists(wav_path):
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
    
    # ADVANCED RED-TEAM FIX: Mask PII before LLM agent sees it
    masked_transcription = PIIMasker.mask(transcription)
    
    return {"transcription": masked_transcription}

def transcription_cleanup_node(state: StudyState, config: RunnableConfig) -> dict[str, Any]:
    """
    GLASS BOX — The ASR Correction Layer.

    Problem being solved:
        Groq Whisper is a phonetic model. When you say "RAG" or "LangChain" while
        whispering, stressed, or with background noise, it mishears sound-alikes:
          "RAG"       -> "WAG", "rag", "rack"
          "LangChain" -> "Landra", "lane chain"
          "Pydantic"  -> "pie dantic", "Py-dan-tick"

    This is NOT about fixing your conceptual understanding of RAG.
    That is Reality Check's job.

    What this node does:
        1. Takes the raw Whisper transcript.
        2. Gives the LLM the raw clipboard text (which usually has correct spelling since
           it was typed/pasted) as a domain vocabulary reference.
        3. Asks the LLM to ONLY fix phonetic ASR errors — never alter meaning.
        4. Returns a clean transcript. The Reality Check downstream will judge
           whether your understanding of RAG was actually correct.

    Black Box boundary:
        The LLM call itself is a black box. You don't control the correction model.
        What you MUST understand: the prompt hard-constrains the LLM to ONLY fix
        transcription artifacts, not re-interpret user statements.

    When to skip:
        If no audio was provided (transcription == standard fallback string), skip cleanup.
    """
    transcription = state.get("transcription", "")
    
    # Skip if transcription is just the fallback (no audio was recorded)
    if not transcription or "No audio explanation provided" in transcription or "Audio recording failed" in transcription:
        logger.info("transcription_cleanup_skipped", reason="no_real_transcription")
        return {}

    # Use clipboard context as the domain vocabulary oracle
    # E.g. if user pasted "RAG pipeline using LangChain", the LLM will know "WAG" is wrong
    context_anchor = state.get("raw_text_context", "").strip()
    
    logger.info("transcription_cleanup_started")

    try:
        llm = LLMRouter.get_primary_synthesizer()
        
        cleanup_prompt = f"""You are a SURGICAL Automatic Speech Recognition (ASR) error corrector.

Your ONLY job is to fix phonetic transcription errors (mishearings) in the voice transcript.

**CONTEXT ANCHOR** (typed/pasted text with correctly-spelled domain terms):
```
{context_anchor[:1500] if context_anchor else "No text context available."}
```

**RAW WHISPER TRANSCRIPT** (may contain ASR mishearings):
```
{transcription}
```

**RULES — READ THESE CAREFULLY:**
1. ONLY fix words that are clearly a phonetic ASR error (sound-alikes). 
   - Examples: "WAG" → "RAG", "landra" → "LangChain", "pie dantic" → "Pydantic"
2. DO NOT change the user's meaning, arguments, or conceptual statements. 
   - If the user said "RAG is like a WAG but better" that's their idea — leave it.
3. DO NOT add words the user didn't say.
4. DO NOT remove words the user said.
5. If the transcript uses a term differently from the context anchor, LEAVE IT — that's
   a conceptual difference for a downstream accuracy checker, not your concern.
6. If you are unsure whether a word is an ASR error or an intentional neologism, LEAVE IT.
7. Return ONLY the corrected transcript text. No preamble, no explanation, no quotes.

**CORRECTED TRANSCRIPT:**"""

        response = llm.invoke(cleanup_prompt)
        cleaned = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        if cleaned:
            logger.info("transcription_cleanup_complete", original_length=len(transcription), cleaned_length=len(cleaned))
            return {"transcription": cleaned}
        else:
            logger.warning("transcription_cleanup_empty_response")
            return {}
            
    except Exception as e:
        # Non-fatal — if cleanup fails, just use the original Whisper output
        logger.warning("transcription_cleanup_failed", error=str(e))
        return {}

def context_precheck_node(state: StudyState, config: RunnableConfig) -> dict[str, Any]:
    """Evaluates if the transcription semantically aligns with the context, preventing hallucinations."""
    
    # If the user is just taking a pure voice note without any pasted text, 
    # there is no baseline text context to check against. Auto-approve to allow voice & image only workflows.
    raw_text = state.get('raw_text_context', '').strip()
    # Check if text is extremely short (e.g. just the # Brain Dump header)
    if len(raw_text) < 150:
        logger.info("context_precheck_skipped_due_to_empty_context")
        return {"context_integrity": ContextIntegrityModel(has_context=True, rejection_reason="No text context provided")}
        
    logger.info("context_precheck_node_started")
    prompt = CONTEXT_PRECHECK_PROMPT.format(
        raw_text_context=state['raw_text_context'],
        transcription=state['transcription']
    )
    
    primary_synthesizer = LLMRouter.get_primary_synthesizer()
    result = primary_synthesizer.generate_structured_output(
        prompt=prompt, 
        images=[], 
        output_schema=ContextIntegrityModel
    )
    
    # System Halt if the assessment fails
    if not result.has_context:
        logger.error("adversarial_or_hallucinated_context_detected", reason=result.rejection_reason)
        raise ValueError(f"Context Shield Activated: {result.rejection_reason}")
        
    return {"context_integrity": result}

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
        primary_synthesizer = LLMRouter.get_primary_synthesizer()
        result = primary_synthesizer.generate_structured_output(
            prompt=prompt, 
            images=[], 
            output_schema=MasterySheetModel
        )
    except Exception as e:
        logger.warning("primary_mastery_failed_falling_back", error=str(e))
        fallback_synthesizer = LLMRouter.get_fallback_synthesizer()
        result = fallback_synthesizer.generate_structured_output(
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
        primary_synthesizer = LLMRouter.get_primary_synthesizer()
        result = primary_synthesizer.generate_structured_output(
            prompt=prompt, 
            images=[], 
            output_schema=QuizList
        )
    except Exception as e:
        logger.warning("primary_quiz_failed_falling_back", error=str(e))
        fallback_synthesizer = LLMRouter.get_fallback_synthesizer()
        result = fallback_synthesizer.generate_structured_output(
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
        primary_synthesizer = LLMRouter.get_primary_synthesizer()
        result = primary_synthesizer.generate_structured_output(
            prompt=prompt, 
            images=[], 
            output_schema=MasterySheetModel
        )
    except Exception as e:
        logger.warning("primary_audit_failed_falling_back", error=str(e))
        fallback_synthesizer = LLMRouter.get_fallback_synthesizer()
        result = fallback_synthesizer.generate_structured_output(
            prompt=prompt, 
            images=[], 
            output_schema=MasterySheetModel
        )
    
    return {"audited_mastery_sheet": result}

