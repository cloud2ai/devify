#!/usr/bin/env python
"""
Haraka Email Integration Full Test

This script tests the complete Haraka email receiving workflow:
1. Create multiple test users (auto_assign mode)
2. Send sample EML files to each user
3. Trigger email fetch
4. Monitor processing workflow
5. Verify final SUCCESS status

Usage:
    # Run from container
    python threadline/tests/integration/haraka_manual_test/run_full_test.py

    # Run from host
    docker exec devify-api-dev python \\
        threadline/tests/integration/haraka_manual_test/run_full_test.py

    # With cleanup
    python threadline/tests/integration/haraka_manual_test/run_full_test.py --cleanup

    # Verbose mode
    python threadline/tests/integration/haraka_manual_test/run_full_test.py --verbose
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

from threadline.tests.integration.haraka_manual_test.test_utils import (
    print_header,
    print_step,
    print_success,
    print_error,
    print_info,
    print_verification_result,
    print_report,
    create_test_users,
    send_test_emails,
    trigger_email_fetch,
    wait_for_all_emails,
    verify_results,
    cleanup_test_users,
)


def main():
    """Main test execution function"""

    parser = argparse.ArgumentParser(
        description='Haraka Email Integration Full Test'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Clean up test data after completion'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Workflow completion timeout in seconds (default: 300)'
    )

    args = parser.parse_args()

    print_header("Haraka Email Integration Full Test")

    user_ids = []
    test_passed = False

    try:
        print_step(1, "Create Test Users")
        users = create_test_users()
        user_ids = [u['user'].id for u in users]

        print_step(2, "Send Test Emails")
        sent_emails = send_test_emails(users)

        if len(sent_emails) == 0:
            print_error("No emails were sent successfully")
            sys.exit(1)

        print_step(3, "Trigger Email Fetch")
        fetch_result = trigger_email_fetch()

        if not fetch_result:
            print_error("Email fetch failed")
            sys.exit(1)

        print_step(4, "Monitor Email Processing")
        email_results = wait_for_all_emails(
            sent_emails,
            timeout=args.timeout
        )

        if len(email_results) == 0:
            print_error("No emails completed processing")
            sys.exit(1)

        print_step(5, "Verify Results")
        test_results = verify_results(email_results)

        for result in test_results:
            print_verification_result(result)

        print_report(test_results)

        all_success = all(
            r['checks']['status_success'] for r in test_results
        )
        test_passed = all_success

    except KeyboardInterrupt:
        print_error("\n\nTest interrupted by user")
        sys.exit(1)

    except Exception as e:
        print_error(f"\n\nTest failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    finally:
        if args.cleanup and user_ids:
            print_info("\nCleaning up test data...")
            cleanup_test_users(user_ids)
        elif user_ids:
            print_info(
                "\nTest data preserved. Use --cleanup flag to remove test users."
            )

    sys.exit(0 if test_passed else 1)


if __name__ == '__main__':
    main()
