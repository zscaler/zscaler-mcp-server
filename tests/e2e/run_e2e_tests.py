#!/usr/bin/env python3
"""
E2E Test Runner for Zscaler MCP Server

This script provides a convenient way to run end-to-end tests with various configurations.
It supports running tests against different models, with different success thresholds,
and provides detailed reporting of test results.

Usage:
    python tests/e2e/run_e2e_tests.py [options]

Examples:
    # Run all E2E tests with default settings
    python tests/e2e/run_e2e_tests.py

    # Run tests with specific models
    python tests/e2e/run_e2e_tests.py --models "gpt-4o-mini,gpt-4o"

    # Run tests with custom success threshold
    python tests/e2e/run_e2e_tests.py --threshold 0.8

    # Run tests with more runs per test
    python tests/e2e/run_e2e_tests.py --runs 5

    # Run specific test module
    python tests/e2e/run_e2e_tests.py --test-path tests/e2e/modules/test_zia.py

    # Quick test run (fewer runs, lower threshold)
    python tests/e2e/run_e2e_tests.py --quick

    # Verbose output
    python tests/e2e/run_e2e_tests.py --verbose
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import pytest


def setup_environment():
    """Set up the test environment."""
    # Add the project root to Python path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)

    print("✅ Environment setup completed")


def run_tests(
    test_path: Optional[str] = None,
    models: Optional[List[str]] = None,
    runs: Optional[int] = None,
    threshold: Optional[float] = None,
    verbose: bool = False,
    quick: bool = False,
) -> int:
    """
    Run the E2E tests with the specified configuration.

    Args:
        test_path: Path to specific test file or directory
        models: List of models to test against
        runs: Number of runs per test
        threshold: Success threshold for tests
        verbose: Enable verbose output
        quick: Quick test mode (fewer runs, lower threshold)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Set up environment variables
    env_vars = {}
    
    if models:
        env_vars["MODELS_TO_TEST"] = ",".join(models)
    
    if runs:
        env_vars["RUNS_PER_TEST"] = str(runs)
    
    if threshold:
        env_vars["SUCCESS_THRESHOLD"] = str(threshold)
    
    if quick:
        # Quick mode: fewer runs, lower threshold
        env_vars.setdefault("RUNS_PER_TEST", "1")
        env_vars.setdefault("SUCCESS_THRESHOLD", "0.5")
        env_vars.setdefault("MODELS_TO_TEST", "gpt-4o-mini")
    
    # Apply environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"📝 Set {key}={value}")

    # Build pytest arguments
    pytest_args = [
        "--tb=short",  # Short traceback format
        "-v",  # Verbose output
    ]
    
    if verbose:
        pytest_args.append("-s")  # Show print statements
        pytest_args.append("--log-cli-level=DEBUG")
    
    # Add test path
    if test_path:
        pytest_args.append(test_path)
    else:
        pytest_args.append("tests/e2e/")
    
    # Add marker for E2E tests
    pytest_args.append("-m")
    pytest_args.append("e2e")
    
    print(f"🚀 Running E2E tests with args: {' '.join(pytest_args)}")
    print("📊 Configuration:")
    print(f"   Models: {os.getenv('MODELS_TO_TEST', 'gpt-4o-mini,gpt-4o')}")
    print(f"   Runs per test: {os.getenv('RUNS_PER_TEST', '2')}")
    print(f"   Success threshold: {os.getenv('SUCCESS_THRESHOLD', '0.1')}")
    print(f"   Test path: {test_path or 'tests/e2e/modules/'}")
    
    # Run the tests
    start_time = time.time()
    exit_code = pytest.main(pytest_args)
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"\n⏱️  Test run completed in {duration:.2f} seconds")
    
    return exit_code


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Run E2E tests for Zscaler MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--test-path",
        help="Path to specific test file or directory (default: all E2E tests)"
    )
    
    parser.add_argument(
        "--models",
        help="Comma-separated list of models to test against (default: gpt-4o-mini,gpt-4o)"
    )
    
    parser.add_argument(
        "--runs",
        type=int,
        help="Number of runs per test (default: 2)"
    )
    
    parser.add_argument(
        "--threshold",
        type=float,
        help="Success threshold for tests (default: 0.1)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test mode (fewer runs, lower threshold)"
    )
    
    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List available test modules"
    )
    
    args = parser.parse_args()
    
    # Set up environment
    setup_environment()
    
    # List available tests if requested
    if args.list_tests:
        test_modules = [
            "tests/e2e/test_zia.py",
            "tests/e2e/test_zpa.py", 
            "tests/e2e/test_zdx.py",
            "tests/e2e/test_zcc.py",
            "tests/e2e/test_zidentity.py"
        ]
        
        print("📋 Available E2E test modules:")
        for module in test_modules:
            if Path(module).exists():
                print(f"   ✅ {module}")
            else:
                print(f"   ❌ {module} (not found)")
        return 0
    
    # Parse models argument
    models = None
    if args.models:
        models = [model.strip() for model in args.models.split(",")]
    
    # Run tests
    exit_code = run_tests(
        test_path=args.test_path,
        models=models,
        runs=args.runs,
        threshold=args.threshold,
        verbose=args.verbose,
        quick=args.quick,
    )
    
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main()) 