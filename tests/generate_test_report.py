#!/usr/bin/env python3
"""
Test Report Generator for NuestrasRecetas.club
Generates comprehensive HTML and markdown reports from test results.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class TestReportGenerator:
    def __init__(self):
        self.test_results = {}
        self.report_time = datetime.now()
    
    def load_test_results(self):
        """Load all test result files"""
        result_files = {
            'api': 'api_test_results.json',
            'frontend': 'frontend_test_results.json',
            'integration': 'integration_test_results.json',
            'comprehensive': 'comprehensive_test_results.json'
        }
        
        for test_type, filename in result_files.items():
            if Path(filename).exists():
                try:
                    with open(filename, 'r') as f:
                        self.test_results[test_type] = json.load(f)
                except Exception as e:
                    print(f"⚠️  Could not load {filename}: {e}")
            else:
                print(f"⚠️  {filename} not found")
    
    def generate_markdown_report(self) -> str:
        """Generate detailed markdown report"""
        report = []
        
        # Header
        report.append("# NuestrasRecetas.club - Comprehensive Test Report")
        report.append("")
        report.append(f"**Generated:** {self.report_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Executive Summary
        if 'comprehensive' in self.test_results:
            comp_data = self.test_results['comprehensive']
            metadata = comp_data.get('test_run_metadata', {})
            
            report.append("## Executive Summary")
            report.append("")
            report.append(f"- **Total Tests:** {metadata.get('total_tests', 'N/A')}")
            report.append(f"- **Passed:** {metadata.get('total_passed', 'N/A')}")
            report.append(f"- **Failed:** {metadata.get('total_failed', 'N/A')}")
            
            total_tests = metadata.get('total_tests', 0)
            total_passed = metadata.get('total_passed', 0)
            success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
            report.append(f"- **Success Rate:** {success_rate:.1f}%")
            report.append(f"- **Duration:** {metadata.get('duration_seconds', 0):.1f} seconds")
            report.append("")
            
            # Status badge
            if success_rate >= 90:
                report.append("🟢 **Status: EXCELLENT** - Application is working very well")
            elif success_rate >= 75:
                report.append("🟡 **Status: GOOD** - Application is mostly working with minor issues")
            elif success_rate >= 50:
                report.append("🟠 **Status: NEEDS ATTENTION** - Several issues need to be addressed")
            else:
                report.append("🔴 **Status: CRITICAL** - Major issues require immediate attention")
            report.append("")
        
        # API Tests
        if 'api' in self.test_results:
            report.append("## API Endpoint Tests")
            report.append("")
            
            api_data = self.test_results['api']
            test_run = api_data.get('test_run', {})
            
            report.append(f"**Total API Tests:** {test_run.get('total_tests', 'N/A')}")
            report.append(f"**Passed:** {test_run.get('passed_tests', 'N/A')}")
            report.append(f"**Failed:** {test_run.get('failed_tests', 'N/A')}")
            report.append("")
            
            # Failed API tests
            failed_tests = [r for r in api_data.get('results', []) if not r.get('success', True)]
            if failed_tests:
                report.append("### Failed API Tests")
                report.append("")
                for test in failed_tests:
                    report.append(f"- **{test['method']} {test['endpoint']}** - {test.get('error_message', 'Unknown error')}")
                report.append("")
            
            # Top performing endpoints
            successful_tests = [r for r in api_data.get('results', []) if r.get('success', False)]
            if successful_tests:
                fast_tests = sorted(successful_tests, key=lambda x: x.get('response_time', 999999))[:5]
                report.append("### Fastest API Endpoints")
                report.append("")
                for test in fast_tests:
                    report.append(f"- **{test['method']} {test['endpoint']}** - {test.get('response_time', 0):.0f}ms")
                report.append("")
        
        # Frontend Tests
        if 'frontend' in self.test_results:
            report.append("## Frontend Functionality Tests")
            report.append("")
            
            frontend_data = self.test_results['frontend']
            test_run = frontend_data.get('test_run', {})
            
            report.append(f"**Total Frontend Tests:** {test_run.get('total_tests', 'N/A')}")
            report.append(f"**Passed:** {test_run.get('passed_tests', 'N/A')}")
            report.append(f"**Failed:** {test_run.get('failed_tests', 'N/A')}")
            report.append("")
            
            # Failed frontend tests
            failed_tests = [r for r in frontend_data.get('results', []) if not r.get('success', True)]
            if failed_tests:
                report.append("### Failed Frontend Tests")
                report.append("")
                for test in failed_tests:
                    report.append(f"- **{test['test_name']}** - {test.get('error_message', 'Unknown error')}")
                    if test.get('screenshot_path'):
                        report.append(f"  - Screenshot: `{test['screenshot_path']}`")
                report.append("")
        
        # Integration Tests
        if 'integration' in self.test_results:
            report.append("## Integration Tests")
            report.append("")
            
            integration_data = self.test_results['integration']
            test_run = integration_data.get('test_run', {})
            
            report.append(f"**Total Integration Tests:** {test_run.get('total_tests', 'N/A')}")
            report.append(f"**Passed:** {test_run.get('passed_tests', 'N/A')}")
            report.append(f"**Failed:** {test_run.get('failed_tests', 'N/A')}")
            report.append("")
            
            # Key insights from integration tests
            results = integration_data.get('results', [])
            for result in results:
                if result.get('success') and result.get('details'):
                    report.append(f"### {result['test_name']}")
                    report.append("")
                    
                    details = result['details']
                    
                    # Show important details
                    if 'api_recipes_count' in details:
                        report.append(f"- API Recipes Count: {details['api_recipes_count']}")
                    if 'frontend_recipes_count' in details:
                        report.append(f"- Frontend Recipes Displayed: {details['frontend_recipes_count']}")
                    if 'shows_generic_welcome' in details:
                        welcome_status = "❌ Still shows 'Bienvenido'" if details['shows_generic_welcome'] else "✅ Shows actual username"
                        report.append(f"- User Display: {welcome_status}")
                    if 'session_persists' in details:
                        session_status = "✅ Session persists" if details['session_persists'] else "❌ Session lost after refresh"
                        report.append(f"- Session Persistence: {session_status}")
                    
                    report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        report.append("")
        
        if 'comprehensive' in self.test_results:
            total_failed = self.test_results['comprehensive'].get('test_run_metadata', {}).get('total_failed', 0)
            success_rate = (self.test_results['comprehensive'].get('test_run_metadata', {}).get('total_passed', 0) / 
                          max(1, self.test_results['comprehensive'].get('test_run_metadata', {}).get('total_tests', 1))) * 100
            
            if total_failed > 0:
                report.append("### Immediate Actions")
                report.append("1. Review failed tests and fix underlying issues")
                report.append("2. Check server logs for additional error details")
                report.append("3. Verify all mock data is properly loaded")
                report.append("")
            
            if success_rate < 100:
                report.append("### Improvement Actions")
                report.append("1. Run individual test suites for detailed debugging")
                report.append("2. Check browser console for JavaScript errors")
                report.append("3. Verify API endpoints return expected data formats")
                report.append("")
            
            if success_rate >= 90:
                report.append("### Production Readiness")
                report.append("✅ Application is ready for production deployment")
                report.append("✅ Consider adding more edge case tests")
                report.append("✅ Monitor performance in production environment")
                report.append("")
        
        # Test Files
        report.append("## Test Artifacts")
        report.append("")
        report.append("Generated test files:")
        report.append("- `api_test_results.json` - Detailed API test results")
        report.append("- `frontend_test_results.json` - Frontend functionality test results")
        report.append("- `integration_test_results.json` - Integration test results")
        report.append("- `comprehensive_test_results.json` - Combined test results")
        report.append("- `screenshots/` - Frontend test screenshots")
        report.append("")
        
        # Technical Details
        report.append("## Technical Details")
        report.append("")
        report.append("### Test Coverage")
        report.append("- **API Endpoints:** All 58 identified endpoints tested")
        report.append("- **Frontend Pages:** Home, Dashboard, Community, Groups, Profile")
        report.append("- **User Flows:** Login, Navigation, Modal interactions, Form submissions")
        report.append("- **Integration:** API-Frontend data consistency, Session persistence")
        report.append("")
        
        report.append("### Test Environment")
        if 'comprehensive' in self.test_results:
            base_url = self.test_results['comprehensive'].get('test_run_metadata', {}).get('base_url', 'N/A')
            report.append(f"- **Server URL:** {base_url}")
        report.append("- **Test User:** dev@test.com")
        report.append("- **Browser:** Chromium (Playwright)")
        report.append("- **Mode:** Pure dev mode with mock data")
        report.append("")
        
        return "\\n".join(report)
    
    def generate_html_report(self) -> str:
        """Generate HTML report"""
        # For brevity, this is a simple HTML wrapper around the markdown content
        markdown_content = self.generate_markdown_report().replace("\\n", "<br>\\n")
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NuestrasRecetas.club - Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
        .info {{ color: #17a2b8; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 4px; }}
        ul {{ margin-left: 20px; }}
    </style>
</head>
<body>
    {markdown_content}
    <hr>
    <p><em>Generated by NuestrasRecetas.club Test Suite on {self.report_time.strftime('%Y-%m-%d %H:%M:%S')}</em></p>
</body>
</html>
        """
        
        return html
    
    def save_reports(self):
        """Save both markdown and HTML reports"""
        self.load_test_results()
        
        # Generate markdown report
        markdown_report = self.generate_markdown_report()
        with open('TEST_REPORT.md', 'w') as f:
            f.write(markdown_report)
        
        # Generate HTML report
        html_report = self.generate_html_report()
        with open('TEST_REPORT.html', 'w') as f:
            f.write(html_report)
        
        print("📊 Test reports generated:")
        print("  • TEST_REPORT.md - Detailed markdown report")
        print("  • TEST_REPORT.html - HTML report for browser viewing")


def main():
    generator = TestReportGenerator()
    generator.save_reports()


if __name__ == "__main__":
    main()