# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LessLLM is a lightweight Python framework for LLM inference with the goal of "doing more with less code/gpu/mem". This is an early-stage project with minimal initial implementation.

## Project Structure

- `lessllm/` - Main Python package directory
- `setup.py` - Package configuration and metadata
- `README.md` - Basic project description

## Development Commands

### Installation
```bash
pip install -e .  # Install in development mode
```

### Package Management
```bash
python setup.py sdist bdist_wheel  # Build distribution packages
pip install -r requirements.txt    # Install dependencies (if requirements.txt exists)
```

## Architecture Notes

This is a minimal Python package setup using setuptools. The current codebase is in its initial state with:
- Basic package structure following Python conventions
- Setup configuration targeting Python 3.6+
- MIT license
- Standard setuptools-based package management

The project appears to be in early development with the core implementation yet to be built out in the `lessllm/` package directory.