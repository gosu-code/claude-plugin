#!/usr/bin/env python3
"""
Comprehensive test suite runner for task_list_md.py
Runs all tests and provides summary report
"""

import unittest
import sys
import os
from pathlib import Path

# Add the test directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Import all test modules
from test_cli_commands import TestTaskListMDCLI
from test_task_parser import TestTaskParser, TestProgressTracker
from test_error_handling import TestErrorHandling
from test_track_progress import TestTrackProgress
from test_auto_file_selection import TestAutoFileSelection
from test_update_task import TestUpdateTaskCommand


def create_test_suite():
    """Create comprehensive test suite"""
    suite = unittest.TestSuite()

    # Add CLI command tests
    suite.addTest(unittest.makeSuite(TestTaskListMDCLI))

    # Add TaskParser tests
    suite.addTest(unittest.makeSuite(TestTaskParser))
    suite.addTest(unittest.makeSuite(TestProgressTracker))

    # Add error handling tests
    suite.addTest(unittest.makeSuite(TestErrorHandling))

    # Add track-progress tests
    suite.addTest(unittest.makeSuite(TestTrackProgress))

    # Add auto file selection tests
    suite.addTest(unittest.makeSuite(TestAutoFileSelection))

    # Add update-task command tests
    suite.addTest(unittest.makeSuite(TestUpdateTaskCommand))

    return suite


def run_tests(verbosity=2):
    """Run all tests with specified verbosity"""
    # Create test suite
    suite = create_test_suite()

    # Create test runner
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        stream=sys.stdout,
        buffer=True
    )

    # Run tests
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")

    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}")

    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\nSuccess rate: {success_rate:.1f}%")

    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        return 1


if __name__ == "__main__":
    # Check if script exists before running tests
    script_path = Path(__file__).parent.parent.parent.parent / "plugins" / "gosu-mcp-core" / "skills" / "task-list-md" / "scripts" / "task_list_md.py"
    if not script_path.exists():
        print(f"❌ Error: Script not found at {script_path}")
        print("Please ensure the task_list_md.py script exists in src/scripts/task_list_md/")
        sys.exit(1)

    # Parse command line arguments
    verbosity = 2
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quiet":
            verbosity = 1
        elif sys.argv[1] == "--verbose":
            verbosity = 2

    # Run tests
    exit_code = run_tests(verbosity)
    sys.exit(exit_code)