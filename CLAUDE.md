# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Raid is an LLM-based multi-agent orchestration system featuring:
- **LLM Control Agent**: An LLM-powered orchestrator operating in ReAct mode (Thought-Action-Observation cycles)
- **LLM Sub-Agents**: Specialized agents running in Docker containers, each with specific tools and capabilities
- **Docker Orchestrator**: Manages Sub-Agent containers and their lifecycle
- **Message Queue Communication**: Agents communicate via MQ for task distribution and results

## Architecture

The system follows a phased development approach:
1. **Phase 1**: LLM Sub-Agent foundation with scripted triggers
2. **Phase 2**: LLM-based Control Agent with ReAct cycles and single Sub-Agent orchestration
3. **Phase 3**: Multi-profile Sub-Agents with expanded Control Agent meta-tools
4. **Phase 4**: Long-term memory (RAG) and external API proxy capabilities
5. **Phase 5**: Production hardening with observability and security

### Key Components
- **Control Agent Meta-Tools**: `dispatch_to_sub_agent()`, `plan_sub_task()`, `discover_sub_agent_profiles()`, etc.
- **Sub-Agent Auto-Configurator**: YAML-based definitions for Sub-Agent profiles
- **LLM Backend Interface**: Abstraction for OpenAI/Ollama integration

## Development Setup

The project currently requires:
- Docker (installed and running)
- UV package manager (based on README reference)

Note: This is an early-stage project (v0.1) with most components still in development phase.

## Context Management

Critical design focus on context management for the Control Agent's LLM:
- **Scratchpad/Working Memory**: T-A-O cycle history for current tasks
- **Long-term Memory**: Archive/RAG system for past task retrieval
- **Token Limit Management**: Strategies for context window optimization

## Security Considerations

- Secure credential/endpoint injection for Sub-Agent LLM access
- Prompt injection protection for Control Agent
- Meta-tool permission controls
- No secrets in code or commits