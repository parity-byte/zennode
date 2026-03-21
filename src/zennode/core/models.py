from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class RealityCheckModel(BaseModel):
    """Pydantic model representing the output of the First-Principles Accuracy Checker."""
    is_accurate: bool = Field(description="Whether the user's explanation was fundamentally accurate.")
    nailed_concepts: list[str] = Field(description="A list of 1-3 bullet points of what the user explained perfectly.")
    misconceptions: list[str] = Field(description="A list of any misconceptions, missed edge cases, or flaws in the user's logic.")
    correction_explanation: str = Field(description="A short, encouraging explanation correcting any misconceptions. Leave empty if 100% accurate.")

class MasterySection(BaseModel):
    """Pydantic model representing a dynamic section in the Mastery Sheet."""
    title: str = Field(description="The header for the section, using emojis (e.g., '🚦 Sub-System Fallbacks' or '🌊 Flow Architecture'). Tailor this dynamically based on the specific concept's depth and seriousness. Generate multiple highly-specific sections if the topic is complex.")
    content: str = Field(description="The markdown content for the section. STRICTLY embed a Mermaid diagram (```mermaid...```) if a system flow or architecture is being mapped. Use aggressive formatting (bolding, tables, bullet points).")

class MasterySheetModel(BaseModel):
    """Pydantic model representing the structured Mastery Sheet."""
    topic_title: str = Field(description="The core topic being discussed.")
    ai_lifecycle_map: str = Field(description="Where this code/concept fits in the standard flow (Ingestion -> Chunking -> Embed -> Retrieve -> Route -> Generate).")
    dynamic_sections: list[MasterySection] = Field(description="A highly dynamic list of deeply interlinked sections breaking down the 'How and Why' of the system. Adapt the length, depth, and specific headers based on the topic's gravity.")

class QuizQuestionModel(BaseModel):
    """Pydantic model representing a spaced-repetition flashcard."""
    question: str = Field(description="A high-level architectural question testing 'how' and 'why' things work together (not rote syntax trivia).")
    answer: str = Field(description="The crisp, concise answer to the question.")

class StudyState(TypedDict):
    """The state graph for the LangGraph pedagogical pipeline."""
    dump_dir: str | None
    obsidian_file_path: str
    audio_file_path: str | None
    raw_images: list[str]
    raw_text_context: str
    transcription: str
    reality_check_results: RealityCheckModel | None
    mastery_sheet: MasterySheetModel | None
    audited_mastery_sheet: MasterySheetModel | None
    quiz_flashcards: list[QuizQuestionModel]
    error: str | None
