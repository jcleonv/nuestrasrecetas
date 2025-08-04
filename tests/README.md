# NuestrasRecetas.club Test Suite

Comprehensive test suite for validating the entire NuestrasRecetas.club application functionality.

## Overview

This test suite provides comprehensive coverage for:
- **API Endpoints:** All 58 Flask endpoints 
- **Frontend Functionality:** User interactions, modals, forms, navigation
- **Integration Testing:** API-Frontend data consistency and user workflows
- **Performance Monitoring:** Response times and load performance

## Test Files

### Core Test Suites
- `test_api_endpoints.py` - Tests all API endpoints with authentication
- `test_frontend_functionality.py` - Browser automation tests using Playwright
- `test_integration.py` - End-to-end workflow testing
- `run_all_tests.py` - Orchestrates all test suites and generates reports

### Utilities
- `generate_test_report.py` - Creates detailed HTML/Markdown reports
- `requirements.txt` - Test dependencies
- `README.md` - This documentation

## Quick Start

### Prerequisites
1. **Flask Server Running:** Start the application server first
   ```bash
   python app.py
   # Server should be running at http://127.0.0.1:8000
   ```

2. **Test Environment:** Ensure you're in "pure dev mode" with mock data loaded

### Running Tests

#### Option 1: Run All Tests (Recommended)
```bash
cd tests/
python run_all_tests.py
```

This will:
- Check server availability
- Install dependencies if needed
- Run all test suites
- Generate comprehensive reports

#### Option 2: Run Individual Test Suites
```bash
# API endpoint tests only
python test_api_endpoints.py

# Frontend functionality tests only
python test_frontend_functionality.py

# Integration tests only
python test_integration.py
```

#### Option 3: Custom Server URL
```bash
python run_all_tests.py http://localhost:5000
```

## Test Results

After running tests, you'll get:

### Console Output
- Real-time test progress
- Pass/fail status for each test
- Performance metrics
- Summary statistics

### Generated Files
- `api_test_results.json` - Detailed API test results
- `frontend_test_results.json` - Frontend test results
- `integration_test_results.json` - Integration test results
- `comprehensive_test_results.json` - Combined results
- `TEST_REPORT.md` - Detailed markdown report
- `TEST_REPORT.html` - HTML report for browser viewing
- `screenshots/` - Screenshots from failed frontend tests

## Test Coverage

### API Endpoints (58 endpoints tested)
✅ Authentication endpoints (`/api/auth/*`)
✅ Recipe CRUD operations (`/api/recipe/*`, `/api/recipes/*`)
✅ Git-for-Recipes functionality (`/api/recipes/*/fork`, `/api/recipes/*/commit`, etc.)
✅ User management (`/api/users/*`, `/api/profile/*`)
✅ Community features (`/api/community/feed`, `/api/posts/*`)
✅ Group functionality (`/api/groups/*`)
✅ Dashboard and statistics (`/api/dashboard/stats`)

### Frontend Functionality
✅ Page loading (Home, Dashboard, Community, Groups)
✅ User authentication flow
✅ Modal open/close functionality
✅ Form submissions
✅ Button interactions
✅ Navigation between pages
✅ Mobile responsiveness
✅ JavaScript error detection

### Integration Testing
✅ User session persistence
✅ API-Frontend data consistency
✅ Mock data integration
✅ Git-for-Recipes workflows
✅ Community feed integration
✅ Profile data consistency

## Authentication

Tests use the dev user credentials:
- **Email:** dev@test.com
- **Password:** dev123

Make sure this user exists in your dev environment.

## Dependencies

Auto-installed by the test runner:
- `requests` - HTTP requests for API testing
- `playwright` - Browser automation for frontend testing

## Troubleshooting

### Server Not Available
```
❌ Server not available at http://127.0.0.1:8000
```
**Solution:** Start the Flask server: `python app.py`

### Missing Dependencies
```
❌ Missing dependencies: playwright, requests
```
**Solution:** Run `python run_all_tests.py` - it will auto-install dependencies

### Browser Installation Issues
```
❌ Playwright browser installation failed
```
**Solution:** 
```bash
pip install playwright
playwright install
```

### Authentication Failures
```
❌ Authentication failed
```
**Solution:** Verify dev@test.com user exists and app is in dev mode

### JavaScript Errors
Frontend tests may detect JavaScript console errors. Check browser console for details.

## Performance Expectations

### Good Performance Indicators
- API response times < 500ms
- Page load times < 3 seconds
- No JavaScript console errors
- 95%+ test success rate

### Warning Signs
- API response times > 1000ms
- Multiple JavaScript errors
- Authentication failures
- Data consistency issues

## Customization

### Adding New Tests
1. Add test methods to appropriate test class
2. Follow the existing pattern for error handling and result logging
3. Update test counts in summary methods

### Modifying Test Data
- Edit test credentials in each test file
- Modify expected data in assertions
- Update mock data expectations

### Custom Assertions
Each test suite has specific success criteria. Modify these in the test methods as needed.

## CI/CD Integration

This test suite can be integrated into CI/CD pipelines:

```bash
# Example CI script
python app.py &  # Start server in background
sleep 5          # Wait for server to start
cd tests/
python run_all_tests.py
kill %1          # Stop server
```

## Contributing

When adding new features to NuestrasRecetas.club:
1. Add corresponding API endpoint tests
2. Add frontend functionality tests if UI is involved
3. Add integration tests for end-to-end workflows
4. Run full test suite before committing

## Support

For issues with the test suite:
1. Check that the Flask server is running and accessible
2. Verify you're in dev mode with mock data
3. Check console output for specific error messages
4. Review generated test reports for detailed information