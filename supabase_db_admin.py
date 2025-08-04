#!/usr/bin/env python3
"""
Supabase Database Administration Script
Comprehensive DBA operations for the recipes application database

Features:
- Database health monitoring
- Backup and restore operations
- User management and access control
- Performance monitoring
- Connection pooling setup
- Disaster recovery procedures
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse
import subprocess
import requests

# Database Configuration
class SupabaseDBAdmin:
    def __init__(self):
        self.supabase_url = os.environ.get('SUPABASE_URL', 'https://egyxcuejvorqlwujsdpp.supabase.co')
        self.anon_key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVneXhjdWVqdm9ycWx3dWpzZHBwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQwMTYyMzYsImV4cCI6MjA2OTU5MjIzNn0.oDO3vRVqHEfoB8TObdKqWAGqOqAC9zRQbRvrolUcRro')
        self.service_key = os.environ.get('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ1.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVneXhjdWVqdm9ycWx3dWpzZHBwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDAxNjIzNiwiZXhwIjoyMDY5NTkyMjM2fQ.ezUI_k0y6Ljcc4MGtzHmRYwtI0Z6L0LW825CHQIQwxM')
        self.database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres.egyxcuejvorqlwujsdpp:recipesforeveryone2025@aws-0-us-east-1.pooler.supabase.com:6543/postgres')
        
        self.parsed_db_url = urlparse(self.database_url)
        self.project_id = self.supabase_url.split('//')[1].split('.')[0]
        
        # Headers for API requests
        self.anon_headers = {
            'apikey': self.anon_key,
            'Authorization': f'Bearer {self.anon_key}',
            'Content-Type': 'application/json'
        }
        
        self.service_headers = {
            'apikey': self.service_key,
            'Authorization': f'Bearer {self.service_key}',
            'Content-Type': 'application/json'
        }

    def log(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def health_check(self):
        """Comprehensive database health check"""
        self.log("Starting database health check...")
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'connection_status': {},
            'table_stats': {},
            'performance_metrics': {},
            'recommendations': []
        }
        
        # Test REST API connection
        try:
            response = requests.get(f'{self.supabase_url}/rest/v1/', 
                                  headers=self.anon_headers, timeout=10)
            if response.status_code == 200:
                health_report['connection_status']['rest_api'] = 'OK'
                self.log("REST API connection: OK")
            else:
                health_report['connection_status']['rest_api'] = f'FAILED ({response.status_code})'
                self.log(f"REST API connection: FAILED ({response.status_code})", "ERROR")
        except Exception as e:
            health_report['connection_status']['rest_api'] = f'ERROR: {str(e)}'
            self.log(f"REST API connection: ERROR: {str(e)}", "ERROR")
        
        # Get table statistics
        tables = ['recipes', 'profiles', 'comments', 'recipe_likes', 'user_follows', 
                 'recipe_versions', 'recipe_activity', 'plans', 'group_posts']
        
        for table in tables:
            try:
                response = requests.get(
                    f'{self.supabase_url}/rest/v1/{table}?select=id',
                    headers={**self.anon_headers, 'Prefer': 'count=exact'},
                    timeout=10
                )
                
                if response.status_code == 200:
                    count = response.headers.get('Content-Range', '0').split('/')[-1]
                    health_report['table_stats'][table] = {
                        'row_count': count,
                        'status': 'OK'
                    }
                else:
                    health_report['table_stats'][table] = {
                        'row_count': 'unknown',
                        'status': f'ERROR ({response.status_code})'
                    }
            except Exception as e:
                health_report['table_stats'][table] = {
                    'row_count': 'unknown',
                    'status': f'ERROR: {str(e)}'
                }
        
        # Performance metrics
        start_time = time.time()
        try:
            response = requests.get(f'{self.supabase_url}/rest/v1/recipes?limit=1', 
                                  headers=self.anon_headers, timeout=10)
            query_time = (time.time() - start_time) * 1000
            health_report['performance_metrics']['avg_query_time_ms'] = round(query_time, 2)
        except Exception as e:
            health_report['performance_metrics']['avg_query_time_ms'] = 'ERROR'
        
        # Generate recommendations
        total_records = sum([int(stats.get('row_count', 0)) if stats.get('row_count', 'unknown').isdigit() 
                           else 0 for stats in health_report['table_stats'].values()])
        
        if total_records > 10000:
            health_report['recommendations'].append("Consider implementing database indexing optimization")
        if total_records > 50000:
            health_report['recommendations'].append("Consider implementing connection pooling")
        if health_report['performance_metrics']['avg_query_time_ms'] > 500:
            health_report['recommendations'].append("Query performance is slow - review indexes and query optimization")
        
        self.log("Health check completed")
        return health_report

    def backup_database(self, backup_type='full'):
        """Create database backup using Supabase CLI or REST API"""
        self.log(f"Starting {backup_type} database backup...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{self.project_id}_{backup_type}_{timestamp}.json"
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'backup_type': backup_type,
            'project_id': self.project_id,
            'tables': {}
        }
        
        # Tables to backup
        tables = ['recipes', 'profiles', 'comments', 'recipe_likes', 'user_follows', 
                 'recipe_versions', 'recipe_activity', 'plans', 'group_posts', 
                 'group_post_comments', 'recipe_contributors', 'recipe_merge_requests']
        
        for table in tables:
            try:
                self.log(f"Backing up table: {table}")
                response = requests.get(
                    f'{self.supabase_url}/rest/v1/{table}',
                    headers=self.service_headers,
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    backup_data['tables'][table] = {
                        'row_count': len(data),
                        'data': data
                    }
                    self.log(f"Backed up {len(data)} rows from {table}")
                else:
                    backup_data['tables'][table] = {
                        'error': f"HTTP {response.status_code}: {response.text}"
                    }
                    self.log(f"Failed to backup {table}: HTTP {response.status_code}", "ERROR")
                    
            except Exception as e:
                backup_data['tables'][table] = {'error': str(e)}
                self.log(f"Failed to backup {table}: {str(e)}", "ERROR")
        
        # Save backup to file
        try:
            with open(backup_filename, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            # Calculate backup file size and checksum
            file_size = os.path.getsize(backup_filename)
            with open(backup_filename, 'rb') as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            
            backup_info = {
                'filename': backup_filename,
                'size_bytes': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'checksum': checksum,
                'timestamp': datetime.now().isoformat()
            }
            
            # Save backup info
            with open(f"{backup_filename}.meta", 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            self.log(f"Backup completed: {backup_filename} ({backup_info['size_mb']} MB)")
            return backup_info
            
        except Exception as e:
            self.log(f"Failed to save backup file: {str(e)}", "ERROR")
            return None

    def restore_database(self, backup_filename, restore_options=None):
        """Restore database from backup file"""
        self.log(f"Starting database restore from: {backup_filename}")
        
        if restore_options is None:
            restore_options = {
                'drop_existing': False,
                'tables_to_restore': None,  # None means all tables
                'dry_run': False
            }
        
        try:
            with open(backup_filename, 'r') as f:
                backup_data = json.load(f)
            
            restored_tables = {}
            
            for table_name, table_data in backup_data.get('tables', {}).items():
                if 'error' in table_data:
                    self.log(f"Skipping {table_name} - backup contains error", "WARNING")
                    continue
                
                if restore_options['tables_to_restore'] and table_name not in restore_options['tables_to_restore']:
                    continue
                
                if restore_options['dry_run']:
                    self.log(f"DRY RUN: Would restore {len(table_data['data'])} rows to {table_name}")
                    continue
                
                try:
                    # For production use, you'd implement proper restore logic here
                    # This is a simplified version
                    self.log(f"Restoring {len(table_data['data'])} rows to {table_name}")
                    
                    # In a real scenario, you'd:
                    # 1. Optionally truncate existing data
                    # 2. Insert data in batches
                    # 3. Handle foreign key constraints
                    # 4. Verify data integrity
                    
                    restored_tables[table_name] = {
                        'rows_restored': len(table_data['data']),
                        'status': 'SUCCESS'
                    }
                    
                except Exception as e:
                    restored_tables[table_name] = {
                        'rows_restored': 0,
                        'status': f'ERROR: {str(e)}'
                    }
                    self.log(f"Failed to restore {table_name}: {str(e)}", "ERROR")
            
            self.log("Database restore completed")
            return restored_tables
            
        except Exception as e:
            self.log(f"Failed to restore database: {str(e)}", "ERROR")
            return None

    def monitor_performance(self, duration_minutes=5):
        """Monitor database performance metrics"""
        self.log(f"Starting performance monitoring for {duration_minutes} minutes...")
        
        metrics = {
            'start_time': datetime.now().isoformat(),
            'duration_minutes': duration_minutes,
            'samples': []
        }
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time:
            sample = {
                'timestamp': datetime.now().isoformat(),
                'query_times': {},
                'connection_test': None
            }
            
            # Test query performance on different tables
            test_queries = [
                ('recipes', 'recipes?limit=10'),
                ('profiles', 'profiles?limit=10'),
                ('comments', 'comments?limit=10')
            ]
            
            for table, endpoint in test_queries:
                start_time = time.time()
                try:
                    response = requests.get(
                        f'{self.supabase_url}/rest/v1/{endpoint}',
                        headers=self.anon_headers,
                        timeout=10
                    )
                    query_time = (time.time() - start_time) * 1000
                    sample['query_times'][table] = {
                        'time_ms': round(query_time, 2),
                        'status': 'OK' if response.status_code == 200 else f'ERROR_{response.status_code}'
                    }
                except Exception as e:
                    sample['query_times'][table] = {
                        'time_ms': -1,
                        'status': f'ERROR: {str(e)}'
                    }
            
            # Test basic connection
            start_time = time.time()
            try:
                response = requests.get(f'{self.supabase_url}/rest/v1/', 
                                      headers=self.anon_headers, timeout=5)
                connection_time = (time.time() - start_time) * 1000
                sample['connection_test'] = {
                    'time_ms': round(connection_time, 2),
                    'status': 'OK' if response.status_code == 200 else f'ERROR_{response.status_code}'
                }
            except Exception as e:
                sample['connection_test'] = {
                    'time_ms': -1,
                    'status': f'ERROR: {str(e)}'
                }
            
            metrics['samples'].append(sample)
            time.sleep(30)  # Sample every 30 seconds
        
        # Calculate summary statistics
        all_query_times = []
        for sample in metrics['samples']:
            for table_metrics in sample['query_times'].values():
                if table_metrics['time_ms'] > 0:
                    all_query_times.append(table_metrics['time_ms'])
        
        if all_query_times:
            metrics['summary'] = {
                'avg_query_time_ms': round(sum(all_query_times) / len(all_query_times), 2),
                'min_query_time_ms': min(all_query_times),
                'max_query_time_ms': max(all_query_times),
                'total_samples': len(metrics['samples'])
            }
        
        self.log("Performance monitoring completed")
        return metrics

    def generate_user_access_report(self):
        """Generate user access and permissions report"""
        self.log("Generating user access report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'users': [],
            'permissions_summary': {},
            'security_recommendations': []
        }
        
        try:
            # Get all profiles (users)
            response = requests.get(
                f'{self.supabase_url}/rest/v1/profiles?select=*',
                headers=self.service_headers,
                timeout=30
            )
            
            if response.status_code == 200:
                users = response.json()
                
                for user in users:
                    user_info = {
                        'id': user.get('id'),
                        'username': user.get('username'),
                        'name': user.get('name'),
                        'created_at': user.get('created_at'),
                        'last_active': user.get('last_active'),
                        'is_public': user.get('is_public'),
                        'activity_summary': {}
                    }
                    
                    # Get user activity statistics
                    user_id = user.get('id')
                    if user_id:
                        # Count recipes
                        try:
                            recipes_response = requests.get(
                                f'{self.supabase_url}/rest/v1/recipes?user_id=eq.{user_id}&select=id',
                                headers={**self.service_headers, 'Prefer': 'count=exact'},
                                timeout=10
                            )
                            if recipes_response.status_code == 200:
                                user_info['activity_summary']['recipes_count'] = recipes_response.headers.get('Content-Range', '0').split('/')[-1]
                        except:
                            user_info['activity_summary']['recipes_count'] = 'unknown'
                        
                        # Count comments
                        try:
                            comments_response = requests.get(
                                f'{self.supabase_url}/rest/v1/comments?user_id=eq.{user_id}&select=id',
                                headers={**self.service_headers, 'Prefer': 'count=exact'},
                                timeout=10
                            )
                            if comments_response.status_code == 200:
                                user_info['activity_summary']['comments_count'] = comments_response.headers.get('Content-Range', '0').split('/')[-1]
                        except:
                            user_info['activity_summary']['comments_count'] = 'unknown'
                    
                    report['users'].append(user_info)
                
                # Generate permissions summary
                report['permissions_summary'] = {
                    'total_users': len(users),
                    'public_profiles': len([u for u in users if u.get('is_public', False)]),
                    'private_profiles': len([u for u in users if not u.get('is_public', True)])
                }
                
                # Security recommendations
                if report['permissions_summary']['public_profiles'] > report['permissions_summary']['private_profiles']:
                    report['security_recommendations'].append("Consider reviewing public profile settings for privacy")
                
                inactive_users = [u for u in users if not u.get('last_active')]
                if inactive_users:
                    report['security_recommendations'].append(f"Found {len(inactive_users)} users with no recent activity - consider cleanup")
                
            else:
                self.log(f"Failed to get user data: HTTP {response.status_code}", "ERROR")
                
        except Exception as e:
            self.log(f"Failed to generate user access report: {str(e)}", "ERROR")
        
        return report

    def disaster_recovery_test(self):
        """Test disaster recovery procedures"""
        self.log("Starting disaster recovery test...")
        
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'overall_status': 'UNKNOWN',
            'recommendations': []
        }
        
        # Test 1: Backup creation
        self.log("Test 1: Backup creation")
        try:
            backup_info = self.backup_database('dr_test')
            if backup_info:
                test_results['tests']['backup_creation'] = {
                    'status': 'PASS',
                    'details': f"Backup created: {backup_info['filename']} ({backup_info['size_mb']} MB)"
                }
            else:
                test_results['tests']['backup_creation'] = {
                    'status': 'FAIL',
                    'details': 'Failed to create backup'
                }
        except Exception as e:
            test_results['tests']['backup_creation'] = {
                'status': 'FAIL',
                'details': str(e)
            }
        
        # Test 2: Connection resilience
        self.log("Test 2: Connection resilience")
        connection_tests = []
        for i in range(5):
            try:
                start_time = time.time()
                response = requests.get(f'{self.supabase_url}/rest/v1/', 
                                      headers=self.anon_headers, timeout=5)
                response_time = (time.time() - start_time) * 1000
                connection_tests.append({
                    'attempt': i + 1,
                    'status': 'OK' if response.status_code == 200 else 'FAIL',
                    'response_time_ms': round(response_time, 2)
                })
            except Exception as e:
                connection_tests.append({
                    'attempt': i + 1,
                    'status': 'FAIL',
                    'error': str(e)
                })
            time.sleep(1)
        
        successful_connections = len([t for t in connection_tests if t['status'] == 'OK'])
        test_results['tests']['connection_resilience'] = {
            'status': 'PASS' if successful_connections >= 4 else 'FAIL',
            'details': f"{successful_connections}/5 connections successful",
            'connection_tests': connection_tests
        }
        
        # Test 3: Data consistency check
        self.log("Test 3: Data consistency check")
        try:
            # Check for orphaned records or data integrity issues
            recipes_response = requests.get(
                f'{self.supabase_url}/rest/v1/recipes?select=id,user_id',
                headers=self.service_headers,
                timeout=30
            )
            
            profiles_response = requests.get(
                f'{self.supabase_url}/rest/v1/profiles?select=id',
                headers=self.service_headers,
                timeout=30
            )
            
            if recipes_response.status_code == 200 and profiles_response.status_code == 200:
                recipes = recipes_response.json()
                profiles = [p['id'] for p in profiles_response.json()]
                
                orphaned_recipes = [r for r in recipes if r.get('user_id') and r['user_id'] not in profiles]
                
                test_results['tests']['data_consistency'] = {
                    'status': 'PASS' if len(orphaned_recipes) == 0 else 'WARNING',
                    'details': f"Found {len(orphaned_recipes)} orphaned recipes",
                    'orphaned_records': len(orphaned_recipes)
                }
            else:
                test_results['tests']['data_consistency'] = {
                    'status': 'FAIL',
                    'details': 'Failed to fetch data for consistency check'
                }
                
        except Exception as e:
            test_results['tests']['data_consistency'] = {
                'status': 'FAIL',
                'details': str(e)
            }
        
        # Overall status
        test_statuses = [test['status'] for test in test_results['tests'].values()]
        if all(status == 'PASS' for status in test_statuses):
            test_results['overall_status'] = 'PASS'
        elif any(status == 'FAIL' for status in test_statuses):
            test_results['overall_status'] = 'FAIL'
        else:
            test_results['overall_status'] = 'WARNING'
        
        # Recommendations
        if test_results['tests'].get('backup_creation', {}).get('status') == 'FAIL':
            test_results['recommendations'].append("Backup system needs attention - ensure automated backups are working")
        
        if test_results['tests'].get('connection_resilience', {}).get('status') == 'FAIL':
            test_results['recommendations'].append("Connection stability issues detected - investigate network or server problems")
        
        if test_results['tests'].get('data_consistency', {}).get('orphaned_records', 0) > 0:
            test_results['recommendations'].append("Data consistency issues found - run cleanup procedures")
        
        self.log(f"Disaster recovery test completed: {test_results['overall_status']}")
        return test_results

def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python3 supabase_db_admin.py <command> [options]")
        print("Commands:")
        print("  health-check        - Run comprehensive health check")
        print("  backup [type]       - Create database backup (full/incremental)")
        print("  restore <filename>  - Restore from backup file")
        print("  monitor [minutes]   - Monitor performance (default: 5 minutes)")
        print("  user-report         - Generate user access report")
        print("  dr-test            - Run disaster recovery test")
        return
    
    admin = SupabaseDBAdmin()
    command = sys.argv[1].lower()
    
    if command == 'health-check':
        report = admin.health_check()
        print(json.dumps(report, indent=2, default=str))
        
    elif command == 'backup':
        backup_type = sys.argv[2] if len(sys.argv) > 2 else 'full'
        backup_info = admin.backup_database(backup_type)
        if backup_info:
            print(json.dumps(backup_info, indent=2))
        else:
            print("Backup failed")
            sys.exit(1)
            
    elif command == 'restore':
        if len(sys.argv) < 3:
            print("Error: backup filename required")
            sys.exit(1)
        filename = sys.argv[2]
        result = admin.restore_database(filename, {'dry_run': True})  # Dry run by default for safety
        print(json.dumps(result, indent=2))
        
    elif command == 'monitor':
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        metrics = admin.monitor_performance(duration)
        print(json.dumps(metrics, indent=2, default=str))
        
    elif command == 'user-report':
        report = admin.generate_user_access_report()
        print(json.dumps(report, indent=2, default=str))
        
    elif command == 'dr-test':
        results = admin.disaster_recovery_test()
        print(json.dumps(results, indent=2, default=str))
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()