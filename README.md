<h1 align="center">
  <br>
  🧠
  <br>
  ZenNode
  <br>
</h1>

<p align="center">
  <a title="License" target="_blank" href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <img src="https://github.com/parity-byte/zennode/actions/workflows/ci.yml/badge.svg" alt="ZenNode CI/CD" style="margin-right: 10px;" />
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version" />
</p>

Say hello to **ZenNode**, your personalized AI cognitive sidekick! Say goodbye to boring, rigid study tools: with ZenNode, your voice notes, lectures, and PDFs are transformed into neuro-inclusive study material exactly formatted for *how your brain works*. ZenNode is a localized, privacy-first AI pipeline powered by LangGraph that lives in your Menubar and writes directly to your local Obsidian Vault.

<p align="center">
  <img src="https://github.com/user-attachments/assets/placeholder-demo.gif" alt="Demo GIF" />
</p>

---

## 📋 Table of Contents
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage (The Personas)](#-the-personas)
- [Roadmap](#-roadmap)
- [Architecture & Open Source](#-architecture--open-source)
- [Contributing](#-contributing)
- [Star History](#-star-history)

---

## 🚀 Installation

**System Requirements:**
- macOS **14 Sonoma** or later (Apple Silicon or Intel)
- Python **3.11** or later
- [uv](https://docs.astral.sh/uv/) (The lightning-fast Python package manager)

### Option 1: Download and Install Manually (Coming Soon!)
*We are currently building a standalone `.dmg` installer so you won't need the terminal! Until then, follow Option 2.*

### Option 2: The Developer Way (Building from Source)

This is the recommended path for hackers, contributors, and early adopters.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/parity-byte/zennode.git
   cd zennode
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up your environment variables**:
   ```bash
   cp .env.example .env
   ```
   Now, open the `.env` file in your favorite text editor. You will see several fields you need to fill out:
   - `GROQ_API_KEY`: Get a free key from [console.groq.com](https://console.groq.com).
   - `GEMINI_API_KEY`: Get a free key from [Google AI Studio](https://aistudio.google.com).
   - `OBSIDIAN_VAULT_PATH`: The absolute file path to the folder on your Mac where your Obsidian notes live (e.g., `/Users/yourname/Documents/ObsidianVault`).
   - `ZENNODE_PROFILE`: This controls the AI's personality! See the [Usage](#-the-personas) section below.

4. **Launch the Menubar App**:
   ```bash
   uv run zennode-app
   ```
   *Note: On your first launch, ZenNode will request Microphone and Accessibility permissions to allow global dictation.*

---

## 🎭 The Personas

ZenNode isn't just one AI—it's a chameleon. Change the `ZENNODE_PROFILE` in your `.env` file to switch how it teaches you:

- 🏎️ `zennode_adhd_skim.md`: **High-speed.** Bullet points only. Zero fluff. For when you need the TL;DR right now.
- 🤿 `zennode_audhd_deep_dive.md`: **The Rabbit Hole.** Connects microscopic details to the big picture using systems thinking.
- 🎨 `zennode_dyslexic_visual.md`: **Highly spatial.** Heavy use of ASCII diagrams, generous spacing, and clear visual hierarchy.
- 🦉 `zennode_socratic_mentor.md`: **The Guide.** Refuses to give you the answer outright. Asks you guiding questions to help you reach the conclusion yourself.

---

## 🗺️ Roadmap

We are constantly building. Here is where we are going:

- [x] **Phase 1: The Core Engine** 🧠 (LangGraph synthesis, Obsidian Sync, Groq/Gemini support)
- [x] **Phase 2: Deep OS Integration** 🍎 (Native macOS Menubar app, Zero-friction global audio recording)
- [x] **Phase 3: The Persona Library** 🎭 (Modular cognitive profiles for neurodivergent learners)
- [ ] **Phase 4: Spaced Repetition (NSR)** 🔁 (Automated flashcard extraction & native Anki export)
- [ ] **Phase 5: Acoustic Reflection** 🎙️ (Voice-to-voice interaction using local STT/TTS)
- [ ] **Phase 6: Cross-Platform Support** 🌍 (Windows & Linux compatibility)

---

## 🏗️ Architecture & Security

We take code quality seriously. ZenNode is built for developers who want to tinker:
- **Agentic Workflows**: Powered entirely by `LangGraph` for deterministic, reliable multi-agent orchestration.
- **Red-Teamed**: Our prompts are actively tested and guarded using `promptfoo` to prevent prompt injection and persona drift.
- **AI Peer Review**: This repository uses **CodeRabbit AI** to autonomously review every Pull Request.
  - No API key leaks.
  - No breaking changes to the state graph.
  - Every commit is structurally scrutinized.

---

## 🤝 Contributing

We’re all about building accessible, empowering tech for neurodivergent folks. Whether you're fixing a bug, adding a new Persona template, or writing docs—we want you! Read our [`CONTRIBUTING.md`](CONTRIBUTING.md) to join the fun.

## 🌟 Star History

<a href="https://star-history.com/#parity-byte/zennode&Timeline">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=parity-byte/zennode&type=Timeline&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=parity-byte/zennode&type=Timeline" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=parity-byte/zennode&type=Timeline" />
 </picture>
</a>

---
*Built with ❤️ for learners who think differently.*
