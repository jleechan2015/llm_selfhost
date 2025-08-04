# Gemini Project Summary: LLM Self-Host Distributed Caching System

This document provides a summary of the `llm_selfhost` project, a distributed caching system for self-hosting Large Language Models (LLMs).

## Project Goal

The primary goal of this project is to significantly reduce the costs of LLM inference by using a distributed caching architecture. It leverages `vast.ai` for affordable GPU instances and Redis Cloud for a centralized semantic cache. The system is designed to be a cost-effective alternative to major cloud providers, targeting an 81% cost reduction.

## Key Technologies

- **LLM Hosting:** `vast.ai` for GPU instances.
- **LLM Serving:** `Ollama` with models like `qwen3-coder`.
- **Caching:** Redis Cloud Enterprise for distributed semantic caching.
- **API:** FastAPI (Python) to create an Anthropic-compatible API proxy.
- **CLI Integration:** Designed for seamless integration with the Claude CLI.
- **Deployment:** Automated installation and startup scripts (`install.sh`, `llm_proxy_start.sh`).

## Core Features

- **Cost-Effective Inference:** Drastically reduces LLM inference costs.
- **Semantic Caching:** Uses sentence embeddings to cache and retrieve semantically similar query responses, improving efficiency.
- **Claude CLI Integration:** Allows users to leverage their self-hosted models through the Claude CLI.
- **Scalability:** Supports multiple "Thinker" nodes (GPU instances) for parallel processing.
- **Performance:** Aims for sub-100ms response times for cached queries.
- **Automated Setup:** Includes scripts for easy installation and configuration.

## Getting Started

1.  **Clone the repository:** `git clone https://github.com/jleechanorg/llm_selfhost.git`
2.  **Run the installer:** `cd llm_selfhost && chmod +x install.sh && ./install.sh`
3.  **Start the system:** `./start_llm_selfhost.sh`
4.  **Integrate with Claude CLI:** Use the provided scripts and environment variables to connect the Claude CLI to the self-hosted proxy.

## Project Structure

- **`api_proxy.py`, `simple_api_proxy.py`**: The core FastAPI application for the API proxy.
- **`install.sh`, `llm_proxy_start.sh`**: Scripts for installation and starting the services.
- **`.claude/`**: Contains scripts and configurations related to Claude CLI integration.
- **`src/`**: Contains JavaScript source code for related services.
- **`docs/`**: Documentation files.
- **`tests/`**: Integration and unit tests.
- **`requirements.txt`, `package.json`**: Python and Node.js dependencies.
