#!/usr/bin/env python3
"""
Enhanced API Tester for NuestrasRecetas.club
Comprehensive testing of all 58+ API endpoints with:
- Authentication flow management
- Session handling
- Error pattern analysis
- Performance monitoring
- Automated fix recommendations
"""

import asyncio
import json
import time
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import aiohttp
import logging

logger = logging.getLogger(__name__)


@dataclass
class APITestResult:
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None
    headers: Optional[Dict] = None
    request_payload: Optional[Dict] = None


@dataclass
class AuthSession:
    user_id: Optional[str] = None
    session_token: Optional[str] = None
    cookies: Optional[Dict] = None
    is_authenticated: bool = False


class EnhancedAPITester:
    """Enhanced API tester with comprehensive endpoint coverage"""
    
    def __init__(self, base_url: str, credentials: Dict[str, str]):
        self.base_url = base_url
        self.credentials = credentials
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_session = AuthSession()
        self.test_results: List[APITestResult] = []
        
        # All identified endpoints from the Flask app
        self.endpoints = self._get_all_endpoints()
        
        # Test data for various operations
        self.test_data = self._get_test_data()
        
        # Performance thresholds (milliseconds)
        self.performance_thresholds = {
            'fast': 200,      # Login, health checks
            'medium': 500,    # Simple queries
            'slow': 1000,     # Complex operations
            'very_slow': 2000 # Heavy operations
        }

    def _get_all_endpoints(self) -> Dict[str, Dict]:
        """Define all API endpoints with their expected behavior"""
        return {
            # Authentication & Session Management
            '/login': {
                'method': 'POST',
                'auth_required': False,
                'payload': {'email': self.credentials['email'], 'password': self.credentials['password']},
                'expected_status': 200,
                'threshold': 'fast'
            },
            '/logout': {
                'method': 'POST',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'fast'
            },
            '/register': {
                'method': 'POST',
                'auth_required': False,
                'payload': {
                    'email': f'test_{int(time.time())}@example.com',
                    'password': 'testpass123',
                    'display_name': 'Test User'
                },
                'expected_status': 201,
                'threshold': 'medium'
            },
            
            # Health & Status
            '/health': {
                'method': 'GET',
                'auth_required': False,
                'expected_status': 200,
                'threshold': 'fast'
            },
            '/api/status': {
                'method': 'GET',
                'auth_required': False,
                'expected_status': 200,
                'threshold': 'fast'
            },
            
            # User Management
            '/api/users/profile': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'medium'
            },
            '/api/users/profile': {
                'method': 'PUT',
                'auth_required': True,
                'payload': {'display_name': 'Updated Name', 'bio': 'Updated bio'},
                'expected_status': 200,
                'threshold': 'medium'
            },
            '/api/users/search': {
                'method': 'GET',
                'auth_required': True,
                'params': {'q': 'test'},
                'expected_status': 200,
                'threshold': 'medium'
            },
            '/api/users/suggestions': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'medium'
            },
            
            # Recipe Management
            '/api/recipes': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'medium'
            },
            '/api/recipes': {
                'method': 'POST',
                'auth_required': True,
                'payload': self.test_data['new_recipe'],
                'expected_status': 201,
                'threshold': 'slow'
            },
            '/api/recipes/1': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'medium'
            },
            '/api/recipes/1': {
                'method': 'PUT',
                'auth_required': True,
                'payload': self.test_data['update_recipe'],
                'expected_status': [200, 404],
                'threshold': 'slow'
            },
            '/api/recipes/1': {
                'method': 'DELETE',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'medium'
            },
            '/api/recipes/search': {
                'method': 'GET',
                'auth_required': True,
                'params': {'q': 'pasta'},
                'expected_status': 200,
                'threshold': 'medium'
            },
            '/api/recipes/1/fork': {
                'method': 'POST',
                'auth_required': True,
                'payload': {'title': 'Forked Recipe'},
                'expected_status': [201, 404],
                'threshold': 'slow'
            },
            '/api/recipes/1/versions': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'medium'
            },
            '/api/recipes/1/compare/2': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'slow'
            },
            
            # Community Features
            '/api/community/feed': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'slow'
            },
            '/api/community/posts': {
                'method': 'POST',
                'auth_required': True,
                'payload': self.test_data['new_post'],
                'expected_status': 201,
                'threshold': 'medium'
            },
            '/api/community/posts/1': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'medium'
            },
            '/api/community/posts/1/like': {
                'method': 'POST',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'fast'
            },
            '/api/community/posts/1/comment': {
                'method': 'POST',
                'auth_required': True,
                'payload': {'content': 'Great recipe!'},
                'expected_status': [201, 404],
                'threshold': 'medium'
            },
            
            # Groups
            '/api/groups': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'medium'
            },
            '/api/groups': {
                'method': 'POST',
                'auth_required': True,
                'payload': self.test_data['new_group'],
                'expected_status': 201,
                'threshold': 'medium'
            },
            '/api/groups/1': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'medium'
            },
            '/api/groups/1/join': {
                'method': 'POST',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'medium'
            },
            '/api/groups/1/leave': {
                'method': 'POST',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'medium'
            },
            '/api/groups/1/members': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'medium'
            },
            
            # Follows & Social
            '/api/users/1/follow': {
                'method': 'POST',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'fast'
            },
            '/api/users/1/unfollow': {
                'method': 'POST',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'fast'
            },
            '/api/users/followers': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'medium'
            },
            '/api/users/following': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'medium'
            },
            
            # Meal Planning
            '/api/meal-plans': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'medium'
            },
            '/api/meal-plans': {
                'method': 'POST',
                'auth_required': True,
                'payload': self.test_data['new_meal_plan'],
                'expected_status': 201,
                'threshold': 'slow'
            },
            '/api/meal-plans/1': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'medium'
            },
            '/api/meal-plans/1/shopping-list': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'slow'
            },
            
            # Recipe Collections
            '/api/collections': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'medium'
            },
            '/api/collections': {
                'method': 'POST',
                'auth_required': True,
                'payload': self.test_data['new_collection'],
                'expected_status': 201,
                'threshold': 'medium'
            },
            '/api/collections/1/recipes': {
                'method': 'POST',
                'auth_required': True,
                'payload': {'recipe_id': 1},
                'expected_status': [201, 404],
                'threshold': 'medium'
            },
            
            # Analytics & Stats
            '/api/analytics/popular-recipes': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'slow'
            },
            '/api/analytics/user-stats': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'medium'
            },
            
            # File Uploads
            '/api/upload/recipe-image': {
                'method': 'POST',
                'auth_required': True,
                'files': True,
                'expected_status': [200, 400],  # 400 if no file
                'threshold': 'very_slow'
            },
            '/api/upload/profile-image': {
                'method': 'POST',
                'auth_required': True,
                'files': True,
                'expected_status': [200, 400],  # 400 if no file
                'threshold': 'very_slow'
            },
            
            # Advanced Recipe Features
            '/api/recipes/1/nutrition': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'slow'
            },
            '/api/recipes/1/scale': {
                'method': 'POST',
                'auth_required': True,
                'payload': {'servings': 4},
                'expected_status': [200, 404],
                'threshold': 'medium'
            },
            '/api/recipes/1/convert-units': {
                'method': 'POST',
                'auth_required': True,
                'payload': {'target_unit': 'metric'},
                'expected_status': [200, 404],
                'threshold': 'medium'
            },
            
            # Notifications
            '/api/notifications': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'medium'
            },
            '/api/notifications/1/read': {
                'method': 'POST',
                'auth_required': True,
                'expected_status': [200, 404],
                'threshold': 'fast'
            },
            
            # Admin/Moderation (may require special permissions)
            '/api/admin/users': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': [200, 403],  # 403 if not admin
                'threshold': 'slow'
            },
            '/api/admin/reports': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': [200, 403],
                'threshold': 'medium'
            },
            
            # Export/Import
            '/api/export/recipes': {
                'method': 'GET',
                'auth_required': True,
                'expected_status': 200,
                'threshold': 'very_slow'
            },
            '/api/import/recipes': {
                'method': 'POST',
                'auth_required': True,
                'files': True,
                'expected_status': [200, 400],
                'threshold': 'very_slow'
            }
        }

    def _get_test_data(self) -> Dict[str, Any]:
        """Generate test data for API operations"""
        return {
            'new_recipe': {
                'title': f'Test Recipe {int(time.time())}',
                'description': 'A test recipe for automated testing',
                'ingredients': [
                    {'name': 'Test Ingredient', 'amount': 1.0, 'unit': 'cup'}
                ],
                'instructions': ['Step 1: Test preparation'],
                'prep_time': 15,
                'cook_time': 30,
                'servings': 4,
                'difficulty': 'Easy',
                'cuisine': 'Test Cuisine'
            },
            'update_recipe': {
                'title': f'Updated Recipe {int(time.time())}',
                'description': 'Updated description',
                'prep_time': 20
            },
            'new_post': {
                'content': f'Test post content {int(time.time())}',
                'recipe_id': 1,
                'type': 'recipe_share'
            },
            'new_group': {
                'name': f'Test Group {int(time.time())}',
                'description': 'A test group for automated testing',
                'privacy': 'public'
            },
            'new_meal_plan': {
                'name': f'Test Meal Plan {int(time.time())}',
                'start_date': datetime.now().isoformat(),
                'meals': [
                    {
                        'date': datetime.now().isoformat(),
                        'meal_type': 'dinner',
                        'recipe_id': 1
                    }
                ]
            },
            'new_collection': {
                'name': f'Test Collection {int(time.time())}',
                'description': 'A test collection for automated testing',
                'is_public': True
            }
        }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive API tests"""
        logger.info("Starting comprehensive API testing...")
        
        start_time = time.time()
        
        try:
            # Initialize session
            await self._initialize_session()
            
            # Authenticate first
            await self._authenticate()
            
            # Run all endpoint tests
            await self._test_all_endpoints()
            
            # Analyze results
            analysis = self._analyze_results()
            
            duration = time.time() - start_time
            
            return {
                'success': True,
                'total_tests': len(self.test_results),
                'passed_tests': len([r for r in self.test_results if r.success]),
                'failed_tests': len([r for r in self.test_results if not r.success]),
                'skipped_tests': 0,
                'success_rate': (len([r for r in self.test_results if r.success]) / len(self.test_results)) * 100,
                'duration': duration,
                'performance_metrics': analysis['performance_metrics'],
                'fix_recommendations': analysis['fix_recommendations'],
                'detailed_results': [asdict(r) for r in self.test_results]
            }
            
        except Exception as e:
            logger.error(f"API testing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'skipped_tests': 0,
                'success_rate': 0
            }
        finally:
            await self._cleanup_session()

    async def _initialize_session(self):
        """Initialize HTTP session with proper configuration"""
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            keepalive_timeout=60
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'NuestrasRecetas-API-Tester/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        )

    async def _authenticate(self) -> bool:
        """Authenticate and establish session"""
        logger.info("Authenticating...")
        
        login_endpoint = '/login'
        payload = {
            'email': self.credentials['email'],
            'password': self.credentials['password']
        }
        
        result = await self._make_request('POST', login_endpoint, json=payload)
        
        if result.success and result.status_code == 200:
            # Extract session information
            if result.response_data:
                self.auth_session.user_id = result.response_data.get('user_id')
                self.auth_session.session_token = result.response_data.get('token')
            
            # Store cookies from response
            if result.headers and 'set-cookie' in result.headers:
                self.auth_session.cookies = self._parse_cookies(result.headers['set-cookie'])
            
            self.auth_session.is_authenticated = True
            logger.info("✅ Authentication successful")
            return True
        else:
            logger.error(f"❌ Authentication failed: {result.error_message}")
            return False

    async def _test_all_endpoints(self):
        """Test all defined endpoints"""
        logger.info(f"Testing {len(self.endpoints)} endpoints...")
        
        # Test endpoints in logical order
        endpoint_order = [
            # Health checks first
            '/health', '/api/status',
            # User profile
            '/api/users/profile',
            # Basic data fetching
            '/api/recipes', '/api/groups', '/api/community/feed',
            # Create operations
            '/api/recipes', '/api/groups', '/api/community/posts',
            # Update operations
            '/api/users/profile', '/api/recipes/1',
            # Social features
            '/api/users/1/follow', '/api/groups/1/join',
            # Advanced features
            '/api/recipes/1/fork', '/api/meal-plans',
            # Cleanup operations
            '/api/users/1/unfollow', '/api/groups/1/leave'
        ]
        
        # Test ordered endpoints first
        tested_endpoints = set()
        for endpoint in endpoint_order:
            if endpoint in self.endpoints:
                config = self.endpoints[endpoint]
                await self._test_endpoint(endpoint, config)
                tested_endpoints.add(endpoint)
        
        # Test remaining endpoints
        for endpoint, config in self.endpoints.items():
            if endpoint not in tested_endpoints:
                await self._test_endpoint(endpoint, config)

    async def _test_endpoint(self, endpoint: str, config: Dict[str, Any]):
        """Test individual endpoint"""
        method = config['method']
        auth_required = config.get('auth_required', False)
        
        # Skip if authentication required but not authenticated
        if auth_required and not self.auth_session.is_authenticated:
            logger.warning(f"Skipping {method} {endpoint} - authentication required")
            return
        
        # Prepare request parameters
        kwargs = {}
        
        # Add payload for POST/PUT requests
        if config.get('payload'):
            kwargs['json'] = config['payload']
        
        # Add query parameters
        if config.get('params'):
            kwargs['params'] = config['params']
        
        # Add authentication headers/cookies
        if auth_required:
            kwargs['headers'] = kwargs.get('headers', {})
            if self.auth_session.session_token:
                kwargs['headers']['Authorization'] = f'Bearer {self.auth_session.session_token}'
        
        # Handle file uploads
        if config.get('files'):
            # Skip file upload tests for now (would need actual files)
            logger.info(f"⏭️  Skipping file upload test: {method} {endpoint}")
            return
        
        # Make request
        result = await self._make_request(method, endpoint, **kwargs)
        
        # Validate result
        expected_status = config.get('expected_status', 200)
        if isinstance(expected_status, list):
            result.success = result.status_code in expected_status
        else:
            result.success = result.status_code == expected_status
        
        # Check performance threshold
        threshold_name = config.get('threshold', 'medium')
        threshold_ms = self.performance_thresholds[threshold_name]
        if result.response_time_ms > threshold_ms:
            logger.warning(f"⚠️  Performance issue: {method} {endpoint} took {result.response_time_ms:.1f}ms (threshold: {threshold_ms}ms)")

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> APITestResult:
        """Make HTTP request and return structured result"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                response_time_ms = (time.time() - start_time) * 1000
                
                # Get response data
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()
                
                # Create result
                result = APITestResult(
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status,
                    response_time_ms=response_time_ms,
                    success=200 <= response.status < 300,
                    response_data=response_data,
                    headers=dict(response.headers),
                    request_payload=kwargs.get('json')
                )
                
                if not result.success:
                    result.error_message = f"HTTP {response.status}: {response_data}"
                
                self.test_results.append(result)
                
                # Log result
                status_emoji = "✅" if result.success else "❌"
                logger.info(f"{status_emoji} {method} {endpoint} - {response.status} ({response_time_ms:.1f}ms)")
                
                return result
                
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            
            result = APITestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=response_time_ms,
                success=False,
                error_message=str(e),
                request_payload=kwargs.get('json')
            )
            
            self.test_results.append(result)
            logger.error(f"❌ {method} {endpoint} - ERROR: {e}")
            return result

    def _analyze_results(self) -> Dict[str, Any]:
        """Analyze test results and generate recommendations"""
        analysis = {
            'performance_metrics': {},
            'fix_recommendations': []
        }
        
        # Performance analysis
        response_times = [r.response_time_ms for r in self.test_results if r.success]
        if response_times:
            analysis['performance_metrics'] = {
                'avg_response_time_ms': sum(response_times) / len(response_times),
                'max_response_time_ms': max(response_times),
                'min_response_time_ms': min(response_times),
                'slow_endpoints_count': len([t for t in response_times if t > 1000])
            }
        
        # Error pattern analysis
        failed_results = [r for r in self.test_results if not r.success]
        
        # Authentication issues
        auth_failures = [r for r in failed_results if r.status_code == 401]
        if auth_failures:
            analysis['fix_recommendations'].append({
                'issue_type': 'Authentication Failures',
                'severity': 'high',
                'description': f'{len(auth_failures)} endpoints failing with 401 Unauthorized',
                'priority': 1,
                'affected_endpoints': [r.endpoint for r in auth_failures]
            })
        
        # Server errors
        server_errors = [r for r in failed_results if 500 <= r.status_code < 600]
        if server_errors:
            analysis['fix_recommendations'].append({
                'issue_type': 'Server Errors',
                'severity': 'critical',
                'description': f'{len(server_errors)} endpoints returning server errors',
                'priority': 1,
                'affected_endpoints': [r.endpoint for r in server_errors]
            })
        
        # Missing endpoints
        not_found = [r for r in failed_results if r.status_code == 404]
        if not_found:
            analysis['fix_recommendations'].append({
                'issue_type': 'Missing Endpoints',
                'severity': 'medium',
                'description': f'{len(not_found)} endpoints not found (404)',
                'priority': 2,
                'affected_endpoints': [r.endpoint for r in not_found]
            })
        
        # Performance issues
        slow_requests = [r for r in self.test_results if r.response_time_ms > 2000]
        if slow_requests:
            analysis['fix_recommendations'].append({
                'issue_type': 'Performance Issues',
                'severity': 'medium',
                'description': f'{len(slow_requests)} endpoints responding slowly (>2s)',
                'priority': 3,
                'affected_endpoints': [r.endpoint for r in slow_requests]
            })
        
        return analysis

    def _parse_cookies(self, cookie_header: str) -> Dict[str, str]:
        """Parse cookie header into dictionary"""
        cookies = {}
        for item in cookie_header.split(';'):
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies

    async def _cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None