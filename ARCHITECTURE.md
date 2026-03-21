# Architecture Overview

Welcome to the **AuDHD Pipeline** architecture documentation. As per our core philosophy, we believe in **High-Signal, Zero-Bullshit Engineering Truth**. 

Below is the **Black Box vs. Glass Box Mental Model** for maintaining and extending this repository.

## 📦 What is a Black Box? (Treat as Magic)
You do not need to understand the underlying mathematics or deep API implementation of these to contribute:
- **Groq Whisper API**: String (audio path) goes in, String (transcription) comes out.
- **Gemini / Groq LLMs**: Prompt goes in, Pydantic Model comes out (via `with_structured_output`).
- **Rumps**: We use it for the macOS native menu bar icon. Treat it as a simple UI wrapper around Python shell commands.

## 🔍 What is a Glass Box? (You MUST Understand This)
If you touch these systems without understanding them, the pipeline will break.

### 1. LangGraph Orchestration (`workflows/graph.py`)
This is the heart of the engine. It is a state machine graph where data flows chronologically.

**Data Flow:**
1. `ingest`: Extracts text/audio paths.
2. `transcribe`: Takes audio -> Returns transcript string.
3. `accuracy_check`: Vision LLM compares the transcript to reality.
4. `synthesize_mastery`: Merges transcript + reality check into a structured "Mastery Sheet".
5. `generate_quizzes`: Generates spaced repetition flashcards.
6. `audit_critique`: Reviews the Master Sheet for Anti-Patterns. 
7. `save_obsidian`: Converts everything to Markdown and writes to the DB.

### 2. Interface Abstractions (`core/interfaces.py`)
Because the community will want to use different tools, we depend entirely on Abstracts.

- `IStorageProvider`: If you want to connect to Notion, implement this interface. Do **not** hardcode Notion logic into the graph.
- `ITranscriptionService`: If you want to use local Whisper.cpp, implement this interface.

### 3. Native macOS Permission Handling (`infrastructure/permissions.py`)
Because we record audio dynamically, macOS will silently kill the background process if we do not explicitly request AVFoundation permissions natively using PyObjC. 
We check for this permission exactly once before spinning up the `rumps` App loop.

## 🚦 Extending the Graph
To add a new AI node to the pipeline:
1. Define its data requirements in `StudyState` (`core/models.py`).
2. Write the node logic in `workflows/nodes.py`. Return a dict matching the `StudyState` update payload.
3. Inject the node into `build_graph()` in `workflows/graph.py`.
