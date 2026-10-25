#!/usr/bin/env python3
"""
Task 2 Runner - Top-Level Wrapper
=================================
This wrapper executes the main Task 2 automation candidate profiling pipeline
located in "code files/run_task2.py".
It allows running either:
    python run_task2.py [args]
or
    python "code files/run_task2.py" [args]
"""
import sys
import runpy
from pathlib import Path

if __name__ == "__main__":
    target_script = Path(__file__).resolve().parent / "code files" / "run_task2.py"
    if not target_script.exists():
        sys.stderr.write(f"Error: Target script not found at {target_script}\n")
        sys.exit(1)
    
    # Run the target script in the same namespace with all command-line arguments preserved
    runpy.run_path(str(target_script), run_name="__main__")
