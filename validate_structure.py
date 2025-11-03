#!/usr/bin/env python3
"""Validate the Orion package structure without requiring dependencies."""

import os
import sys
from pathlib import Path

def check_file(path, description):
    """Check if a file exists."""
    if Path(path).exists():
        print(f"✓ {description}: {path}")
        return True
    else:
        print(f"✗ {description} missing: {path}")
        return False

def check_python_file(path, description):
    """Check if a Python file exists and has basic syntax."""
    if not check_file(path, description):
        return False
    
    try:
        with open(path, 'r') as f:
            code = f.read()
            compile(code, path, 'exec')
        return True
    except SyntaxError as e:
        print(f"  ✗ Syntax error: {e}")
        return False

def main():
    """Validate package structure."""
    print("Validating Orion package structure...\n")
    
    checks = [
        # Core files
        (check_file, "README.md", "README"),
        (check_file, "LICENSE", "License file"),
        (check_file, "requirements.txt", "Requirements file"),
        (check_file, "setup.py", "Setup script"),
        (check_file, ".gitignore", "Gitignore"),
        
        # Config
        (check_file, "config/orion.yaml", "Default config"),
        
        # Package
        (check_python_file, "orion/__init__.py", "Package init"),
        (check_python_file, "orion/cli.py", "CLI module"),
        
        # Core modules
        (check_python_file, "orion/core/__init__.py", "Core init"),
        (check_python_file, "orion/core/config.py", "Config loader"),
        (check_python_file, "orion/core/embeddings.py", "Embedding model"),
        (check_python_file, "orion/core/memory.py", "Memory manager"),
        (check_python_file, "orion/core/retrieval.py", "RAG retriever"),
        (check_python_file, "orion/core/llm_client.py", "LLM client"),
        (check_python_file, "orion/core/assistant.py", "Main assistant"),
        
        # Utils
        (check_python_file, "orion/utils/__init__.py", "Utils init"),
        
        # Examples
        (check_python_file, "examples/basic_usage.py", "Basic usage example"),
        (check_python_file, "examples/emotion_weighted.py", "Emotion-weighted example"),
        
        # Documentation
        (check_file, "USAGE.md", "Usage documentation"),
    ]
    
    results = []
    for check_func, path, desc in checks:
        results.append(check_func(path, desc))
    
    print(f"\n{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"Validation Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("✓ All checks passed! Package structure is valid.")
        return 0
    else:
        print(f"✗ {total - passed} check(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
