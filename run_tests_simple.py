#!/usr/bin/env python3
"""
Simple Test Runner - Run tests without complex orchestration
"""

import sys
import os
import json
import asyncio
from datetime import datetime

# Add tests directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tests'))

# Import test modules
from advanced_test_orchestrator import AdvancedTestOrchestrator


async def main():
    """Run the test suite"""
    print("\n" + "="*80)
    print("🚀 LAUNCHING TEST SUITE")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # Create orchestrator
    orchestrator = AdvancedTestOrchestrator()
    
    try:
        # Run comprehensive tests
        results = await orchestrator.run_comprehensive_tests(env_name='dev')
        
        # Save results
        with open('test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Display summary
        print("\n" + "="*80)
        print("📊 TEST EXECUTION SUMMARY")
        print("="*80)
        
        if 'summary' in results:
            summary = results['summary']
            print(f"\n📈 Overall Metrics:")
            print(f"   Total Tests: {summary.get('total_tests', 0)}")
            print(f"   Passed: {summary.get('passed_tests', 0)} ✅")
            print(f"   Failed: {summary.get('failed_tests', 0)} ❌")
            print(f"   Success Rate: {summary.get('success_rate', 0):.1f}%")
            print(f"   Duration: {summary.get('duration', 0):.2f}s")
        
        # Display critical issues
        if 'critical_issues' in results:
            issues = results['critical_issues']
            if issues:
                print(f"\n🚨 Critical Issues Found: {len(issues)}")
                for issue in issues[:3]:  # Show top 3
                    print(f"   - {issue}")
        
        # Display report location
        if 'report_path' in results:
            print(f"\n📄 Detailed Report: {results['report_path']}")
        
        print("\n" + "="*80)
        
        # Exit with appropriate code
        if summary and summary.get('success_rate', 0) >= 80:
            print("✅ TEST SUITE PASSED")
            sys.exit(0)
        else:
            print("❌ TEST SUITE FAILED")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())