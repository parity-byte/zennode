from typing import Any

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from zennode.core.models import StudyState
from zennode.infrastructure.config import Config
from zennode.infrastructure.obsidian import ObsidianConnector
from zennode.workflows.nodes import (
    audit_critique_node,
    ingest_node,
    mastery_synthesis_node,
    quiz_generation_node,
    reality_check_node,
    transcribe_node,
)

logger = structlog.get_logger(__name__)

def obsidian_writer_node(state: StudyState, config: RunnableConfig) -> dict[str, Any]:
    """Formats the structured Pydantic models into Markdown and appends to the Obsidian file."""
    logger.info("obsidian_writer_node_started")
    
    rc = state.get("reality_check_results")
    ms = state.get("audited_mastery_sheet") or state.get("mastery_sheet")
    quizzes = state.get("quiz_flashcards", [])
    
    if not ms:
        logger.error("missing_mastery_sheet")
        raise ValueError("Cannot write to Obsidian without a Mastery Sheet.")

    # Format the reality check section
    rc_markdown = ""
    if rc:
        rc_markdown = f"""## 🚨 Reality Check & First Principles Debate
*How accurate was your voice-dump explanation?*
- **Verdict**: {'✅ Fundamentally Accurate' if rc.is_accurate else '❌ Needs Review'}
- **✅ What you nailed:**
""" + "\n".join([f"  - {item}" for item in rc.nailed_concepts]) + """
- **❌ Misconceptions / Missed Edge Cases:**
""" + "\n".join([f"  - {item}" for item in rc.misconceptions]) + f"""

> [!NOTE] Builder's Correction
> {rc.correction_explanation}

"""

    dynamic_sections_markdown = ""
    for sec in ms.dynamic_sections:
        dynamic_sections_markdown += f"## {sec.title}\n{sec.content}\n\n"

    # Format the Mastery Sheet
    ms_markdown = f"""# Mastery: {ms.topic_title}

{rc_markdown}

## 🗺 The AI Lifecycle Map
{ms.ai_lifecycle_map}

{dynamic_sections_markdown}"""

    # Format the Spaced Repetition Flashcards
    quiz_markdown = """## 🧠 Mental Map Revision (Flashcards)
*Review these questions to solidify your architectural understanding.*
"""
    for idx, q in enumerate(quizzes):
        quiz_markdown += f"- **Q{idx+1}:** {q.question}\n  - *A:* {q.answer}\n"

    final_markdown = ms_markdown + quiz_markdown

    import os
    import shutil
    
    # Upsert to an Obsidian structured Topic Note
    vault_path = Config.get_obsidian_vault_path()
    
    raw_context = state.get('raw_text_context', '')
    raw_images = state.get('raw_images', [])
    assets_dir = os.path.join(vault_path, "assets")
    
    if raw_images:
        os.makedirs(assets_dir, exist_ok=True)
        for img_path in raw_images:
            if os.path.exists(img_path):
                # Use the dump timestamp folder name to keep image names unique
                dump_dir_name = os.path.basename(os.path.dirname(img_path))
                orig_name = os.path.basename(img_path)
                unique_img_name = f"{dump_dir_name}_{orig_name}"
                dest_path = os.path.join(assets_dir, unique_img_name)
                
                shutil.copy2(img_path, dest_path)
                raw_context += f"\n\n![[{unique_img_name}]]"

    storage_provider = ObsidianConnector()
    storage_provider.upsert_topic_file(
        vault_path=vault_path,
        topic_title=ms.topic_title,
        content_to_write=final_markdown,
        raw_context=raw_context
    )
    
    # Check if we originally started from a Daily Dump log file. If so, append the newly created Topic link back to the dump file.
    dump_file = state.get('obsidian_file_path', '')
    if dump_file and "Brain_Dump_" in dump_file and os.path.exists(dump_file):
        try:
            with open(dump_file, "a", encoding="utf-8") as f:
                f.write(f"\n- 🧠 Synthesized into Topic: [[{ms.topic_title}]]\n")
        except Exception as e:
            logger.warning("failed_to_link_back_to_dump", error=str(e))
    
    return {}

def build_graph() -> Any:
    """Compiles the AuDHD Pedagogical LangGraph."""
    logger.info("building_study_pipeline_graph")
    
    builder = StateGraph(StudyState)
    
    # Add Nodes
    builder.add_node("ingest", ingest_node)
    builder.add_node("transcribe", transcribe_node)
    builder.add_node("accuracy_check", reality_check_node)
    builder.add_node("synthesize_mastery", mastery_synthesis_node)
    builder.add_node("generate_quizzes", quiz_generation_node)
    builder.add_node("audit_critique", audit_critique_node)
    builder.add_node("save_obsidian", obsidian_writer_node)
    
    # Add Edges
    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "transcribe")
    builder.add_edge("transcribe", "accuracy_check")
    builder.add_edge("accuracy_check", "synthesize_mastery")
    builder.add_edge("synthesize_mastery", "generate_quizzes")
    builder.add_edge("generate_quizzes", "audit_critique")
    builder.add_edge("audit_critique", "save_obsidian")
    builder.add_edge("save_obsidian", END)
    
    # We could add an exact checkpointer here (e.g., MemorySaver for now)
    # Using memory saver for fault-tolerance in memory. For persistent, use SqliteSaver.
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    
    return builder.compile(checkpointer=memory)

pipeline_graph = build_graph()
