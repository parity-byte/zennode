"""
Core System Prompts for ZenNode.
The core persona dictates how the agent thinks and communicates,
while the node-specific prompts dictate the task mechanics.
"""

import os
from zennode.infrastructure.config import Config

PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR = os.path.join(PROMPTS_DIR, "profiles")
USER_TEMPLATES_DIR = Config.get_templates_path()

def _load_prompt(filename: str) -> str:
    """Helper method to load a Markdown prompt template from disk."""
    with open(os.path.join(PROMPTS_DIR, filename), encoding="utf-8") as f:
        return f.read()

def _load_profile(profile_name: str) -> str:
    """Load the active ZenNode learning profile."""
    # 1. Try User Templates Folder First
    path = os.path.join(USER_TEMPLATES_DIR, profile_name)
    if not os.path.exists(path):
        # 2. Try the Built-In Templates Folder Next
        path = os.path.join(PROFILES_DIR, profile_name)
        if not os.path.exists(path):
            # 3. Fallback to default
            path = os.path.join(PROFILES_DIR, "zennode_audhd_deep_dive.md")
            
    with open(path, encoding="utf-8") as f:
        return f.read()

# Load the active profile from the environment (default to deep_dive)
ACTIVE_PROFILE_NAME = os.getenv("ZENNODE_PROFILE", "zennode_audhd_deep_dive.md")
CORE_PERSONA = _load_profile(ACTIVE_PROFILE_NAME)

# Combine Persona with Node-Specific logic to ensure the agent maintains character while executing the node constraint
CONTEXT_PRECHECK_PROMPT = CORE_PERSONA + "\n\n---\n\n" + _load_prompt("CONTEXT_PRECHECK.md")
REALITY_CHECK_PROMPT = CORE_PERSONA + "\n\n---\n\n" + _load_prompt("REALITY_CHECK.md")
MASTERY_SYNTHESIS_PROMPT = CORE_PERSONA + "\n\n---\n\n" + _load_prompt("MASTERY_SYNTHESIS.md")
QUIZ_GENERATION_PROMPT = CORE_PERSONA + "\n\n---\n\n" + _load_prompt("QUIZ_GENERATION.md")
AUDIT_CRITIQUE_PROMPT = CORE_PERSONA + "\n\n---\n\n" + _load_prompt("AUDIT_CRITIQUE.md")
