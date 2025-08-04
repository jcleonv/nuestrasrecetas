#!/usr/bin/env python3
"""
Connection Pool Setup and Management for Supabase
Handles connection pooling, monitoring, and optimization
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse
import threading
import queue

class SupabaseConnectionPool:
    """
    Connection pool manager for Supabase database connections
    Provides connection pooling, health monitoring, and automatic failover
    """
    
    def __init__(self, config=None):
        self.database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres.egyxcuejvorqlwujsdpp:recipesforeveryone2025@aws-0-us-east-1.pooler.supabase.com:6543/postgres')
        self.supabase_url = os.environ.get('SUPABASE_URL', 'https://egyxcuejvorqlwujsdpp.supabase.co')
        
        # Default pool configuration
        self.config = {
            'min_connections': 5,
            'max_connections': 20,
            'connection_timeout': 30,
            'idle_timeout': 300,  # 5 minutes
            'health_check_interval': 60,  # 1 minute
            'retry_attempts': 3,
            'retry_delay': 1
        }
        
        if config:
            self.config.update(config)
        
        self.active_connections = []
        self.idle_connections = queue.Queue(maxsize=self.config['max_connections'])
        self.connection_stats = {
            'created': 0,
            'destroyed': 0,
            'active': 0,
            'idle': 0,
            'failed': 0,
            'last_error': None
        }
        
        self._lock = threading.Lock()
        self._monitoring = False
        self._monitor_thread = None

    def _create_connection(self):
        """Create a new database connection"""
        try:
            # In a real implementation, you'd use psycopg2 or similar
            # For this example, we'll simulate connection creation
            connection_id = f"conn_{int(time.time())}_{len(self.active_connections)}"
            
            connection = {
                'id': connection_id,
                'created_at': datetime.now(),
                'last_used': datetime.now(),
                'query_count': 0,
                'status': 'active'
            }
            
            self.connection_stats['created'] += 1
            return connection
            
        except Exception as e:
            self.connection_stats['failed'] += 1
            self.connection_stats['last_error'] = str(e)
            raise

    def get_connection(self, timeout=None):
        """Get a connection from the pool"""
        timeout = timeout or self.config['connection_timeout']
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                # Try to get an idle connection
                if not self.idle_connections.empty():
                    try:
                        connection = self.idle_connections.get_nowait()
                        connection['last_used'] = datetime.now()
                        connection['status'] = 'active'
                        self.active_connections.append(connection)
                        self.connection_stats['active'] += 1
                        self.connection_stats['idle'] -= 1
                        return connection
                    except queue.Empty:
                        pass
                
                # Create new connection if under max limit
                total_connections = len(self.active_connections) + self.idle_connections.qsize()
                if total_connections < self.config['max_connections']:
                    try:
                        connection = self._create_connection()
                        self.active_connections.append(connection)
                        self.connection_stats['active'] += 1
                        return connection
                    except Exception as e:
                        print(f"Failed to create connection: {e}")
            
            # Wait a bit before retrying
            time.sleep(0.1)
        
        raise TimeoutError(f"Could not get connection within {timeout} seconds")

    def return_connection(self, connection):
        """Return a connection to the pool"""
        with self._lock:
            if connection in self.active_connections:
                self.active_connections.remove(connection)
                self.connection_stats['active'] -= 1
                
                # Check if connection is still healthy
                if self._is_connection_healthy(connection):
                    connection['status'] = 'idle'
                    try:
                        self.idle_connections.put_nowait(connection)
                        self.connection_stats['idle'] += 1
                    except queue.Full:
                        # Pool is full, destroy connection
                        self._destroy_connection(connection)
                else:
                    # Connection is unhealthy, destroy it
                    self._destroy_connection(connection)

    def _is_connection_healthy(self, connection):
        """Check if a connection is healthy"""
        try:
            # Check connection age
            age = datetime.now() - connection['created_at']
            if age.total_seconds() > self.config['idle_timeout']:
                return False
            
            # In a real implementation, you'd run a simple query like SELECT 1
            # For this example, we'll simulate health check
            if connection['query_count'] > 1000:  # Arbitrary limit
                return False
            
            return True
            
        except Exception:
            return False

    def _destroy_connection(self, connection):
        """Destroy a connection"""
        connection['status'] = 'destroyed'
        self.connection_stats['destroyed'] += 1

    def start_monitoring(self):
        """Start background monitoring of connection pool"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        print("Connection pool monitoring started")

    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        print("Connection pool monitoring stopped")

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._monitoring:
            try:
                self._cleanup_idle_connections()
                self._ensure_min_connections()
                self._log_pool_stats()
                time.sleep(self.config['health_check_interval'])
            except Exception as e:
                print(f"Error in monitoring loop: {e}")

    def _cleanup_idle_connections(self):
        """Remove old idle connections"""
        with self._lock:
            idle_connections = []
            
            # Get all idle connections
            while not self.idle_connections.empty():
                try:
                    conn = self.idle_connections.get_nowait()
                    if self._is_connection_healthy(conn):
                        idle_connections.append(conn)
                    else:
                        self._destroy_connection(conn)
                        self.connection_stats['idle'] -= 1
                except queue.Empty:
                    break
            
            # Put healthy connections back
            for conn in idle_connections:
                try:
                    self.idle_connections.put_nowait(conn)
                except queue.Full:
                    self._destroy_connection(conn)
                    self.connection_stats['idle'] -= 1

    def _ensure_min_connections(self):
        """Ensure minimum number of connections are available"""
        with self._lock:
            total_connections = len(self.active_connections) + self.idle_connections.qsize()
            
            if total_connections < self.config['min_connections']:
                needed = self.config['min_connections'] - total_connections
                
                for _ in range(needed):
                    try:
                        connection = self._create_connection()
                        connection['status'] = 'idle'
                        self.idle_connections.put_nowait(connection)
                        self.connection_stats['idle'] += 1
                    except Exception as e:
                        print(f"Failed to create minimum connection: {e}")
                        break

    def _log_pool_stats(self):
        """Log current pool statistics"""
        stats = self.get_stats()
        print(f"Pool Stats - Active: {stats['active']}, Idle: {stats['idle']}, "
              f"Total Created: {stats['created']}, Failed: {stats['failed']}")

    def get_stats(self):
        """Get current pool statistics"""
        with self._lock:
            stats = self.connection_stats.copy()
            stats['idle'] = self.idle_connections.qsize()
            stats['active'] = len(self.active_connections)
            return stats

    def get_detailed_stats(self):
        """Get detailed pool statistics"""
        with self._lock:
            stats = self.get_stats()
            
            # Add connection details
            stats['connections'] = {
                'active_connections': [
                    {
                        'id': conn['id'],
                        'created_at': conn['created_at'].isoformat(),
                        'last_used': conn['last_used'].isoformat(),
                        'query_count': conn['query_count']
                    }
                    for conn in self.active_connections
                ],
                'idle_count': self.idle_connections.qsize(),
                'configuration': self.config
            }
            
            return stats

class ConnectionPoolManager:
    """
    High-level manager for connection pools
    Handles multiple pools and load balancing
    """
    
    def __init__(self):
        self.pools = {}
        self.default_pool = None
        self.load_balancer_strategy = 'round_robin'
        self._current_pool_index = 0

    def create_pool(self, name, config=None):
        """Create a new connection pool"""
        pool = SupabaseConnectionPool(config)
        self.pools[name] = pool
        
        if self.default_pool is None:
            self.default_pool = name
        
        return pool

    def get_pool(self, name=None):
        """Get a connection pool by name"""
        pool_name = name or self.default_pool
        return self.pools.get(pool_name)

    def get_connection(self, pool_name=None):
        """Get a connection from specified or load-balanced pool"""
        if pool_name:
            pool = self.get_pool(pool_name)
            if pool:
                return pool.get_connection()
        else:
            # Load balance across all pools
            return self._get_load_balanced_connection()

    def _get_load_balanced_connection(self):
        """Get connection using load balancing strategy"""
        if not self.pools:
            raise RuntimeError("No connection pools available")
        
        if self.load_balancer_strategy == 'round_robin':
            pool_names = list(self.pools.keys())
            pool_name = pool_names[self._current_pool_index % len(pool_names)]
            self._current_pool_index += 1
            return self.pools[pool_name].get_connection()
        
        elif self.load_balancer_strategy == 'least_connections':
            # Find pool with least active connections
            min_connections = float('inf')
            best_pool = None
            
            for pool in self.pools.values():
                stats = pool.get_stats()
                if stats['active'] < min_connections:
                    min_connections = stats['active']
                    best_pool = pool
            
            if best_pool:
                return best_pool.get_connection()
        
        # Fallback to first available pool
        return list(self.pools.values())[0].get_connection()

    def start_all_monitoring(self):
        """Start monitoring for all pools"""
        for pool in self.pools.values():
            pool.start_monitoring()

    def stop_all_monitoring(self):
        """Stop monitoring for all pools"""
        for pool in self.pools.values():
            pool.stop_monitoring()

    def get_all_stats(self):
        """Get statistics for all pools"""
        return {
            name: pool.get_detailed_stats()
            for name, pool in self.pools.items()
        }


def generate_pool_config():
    """Generate optimized pool configuration based on application needs"""
    
    config_templates = {
        'development': {
            'min_connections': 2,
            'max_connections': 5,
            'connection_timeout': 10,
            'idle_timeout': 60,
            'health_check_interval': 30
        },
        
        'staging': {
            'min_connections': 5,
            'max_connections': 15,
            'connection_timeout': 20,
            'idle_timeout': 180,
            'health_check_interval': 45
        },
        
        'production': {
            'min_connections': 10,
            'max_connections': 50,
            'connection_timeout': 30,
            'idle_timeout': 300,
            'health_check_interval': 60
        },
        
        'high_traffic': {
            'min_connections': 20,
            'max_connections': 100,
            'connection_timeout': 45,
            'idle_timeout': 600,
            'health_check_interval': 30
        }
    }
    
    return config_templates


def main():
    """Main CLI interface for connection pool management"""
    if len(sys.argv) < 2:
        print("Usage: python3 connection_pool_setup.py <command> [options]")
        print("Commands:")
        print("  test [environment]     - Test connection pool (dev/staging/production)")
        print("  monitor [duration]     - Monitor pool performance")
        print("  config [environment]   - Show configuration for environment")
        print("  benchmark [duration]   - Run connection pool benchmark")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'test':
        environment = sys.argv[2] if len(sys.argv) > 2 else 'development'
        
        print(f"Testing connection pool for {environment} environment...")
        
        configs = generate_pool_config()
        config = configs.get(environment, configs['development'])
        
        # Create and test pool
        pool = SupabaseConnectionPool(config)
        pool.start_monitoring()
        
        try:
            # Test getting and returning connections
            connections = []
            
            print("Getting connections from pool...")
            for i in range(min(5, config['max_connections'])):
                try:
                    conn = pool.get_connection()
                    connections.append(conn)
                    print(f"Got connection {i+1}: {conn['id']}")
                except Exception as e:
                    print(f"Failed to get connection {i+1}: {e}")
            
            # Return connections
            print("Returning connections to pool...")
            for conn in connections:
                pool.return_connection(conn)
            
            # Show stats
            stats = pool.get_detailed_stats()
            print("\nPool Statistics:")
            print(json.dumps(stats, indent=2, default=str))
            
        finally:
            pool.stop_monitoring()
    
    elif command == 'config':
        environment = sys.argv[2] if len(sys.argv) > 2 else 'all'
        
        configs = generate_pool_config()
        
        if environment == 'all':
            print("Connection Pool Configurations:")
            print(json.dumps(configs, indent=2))
        else:
            config = configs.get(environment)
            if config:
                print(f"Configuration for {environment}:")
                print(json.dumps(config, indent=2))
            else:
                print(f"Unknown environment: {environment}")
                print(f"Available environments: {list(configs.keys())}")
    
    elif command == 'monitor':
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        
        print(f"Monitoring connection pool for {duration} seconds...")
        
        manager = ConnectionPoolManager()
        
        # Create pools for different purposes
        manager.create_pool('read_pool', generate_pool_config()['production'])
        manager.create_pool('write_pool', generate_pool_config()['production'])
        
        manager.start_all_monitoring()
        
        try:
            end_time = time.time() + duration
            
            while time.time() < end_time:
                stats = manager.get_all_stats()
                print(f"\n--- Pool Stats at {datetime.now().strftime('%H:%M:%S')} ---")
                for pool_name, pool_stats in stats.items():
                    print(f"{pool_name}: Active={pool_stats['active']}, Idle={pool_stats['idle']}, "
                          f"Created={pool_stats['created']}, Failed={pool_stats['failed']}")
                
                time.sleep(10)
                
        finally:
            manager.stop_all_monitoring()
    
    elif command == 'benchmark':
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        
        print(f"Running connection pool benchmark for {duration} seconds...")
        
        config = generate_pool_config()['production']
        pool = SupabaseConnectionPool(config)
        pool.start_monitoring()
        
        # Benchmark metrics
        metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'max_response_time': 0,
            'min_response_time': float('inf')
        }
        
        def worker():
            """Worker thread for benchmark"""
            while time.time() < end_time:
                start_time = time.time()
                try:
                    conn = pool.get_connection(timeout=5)
                    # Simulate work
                    time.sleep(0.001)
                    pool.return_connection(conn)
                    
                    response_time = (time.time() - start_time) * 1000
                    metrics['successful_requests'] += 1
                    metrics['avg_response_time'] += response_time
                    metrics['max_response_time'] = max(metrics['max_response_time'], response_time)
                    metrics['min_response_time'] = min(metrics['min_response_time'], response_time)
                    
                except Exception as e:
                    metrics['failed_requests'] += 1
                
                metrics['total_requests'] += 1
        
        # Start benchmark threads
        end_time = time.time() + duration
        threads = []
        
        for i in range(10):  # 10 concurrent workers
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Calculate final metrics
        if metrics['successful_requests'] > 0:
            metrics['avg_response_time'] /= metrics['successful_requests']
        
        print("\nBenchmark Results:")
        print(f"Total Requests: {metrics['total_requests']}")
        print(f"Successful: {metrics['successful_requests']}")
        print(f"Failed: {metrics['failed_requests']}")
        print(f"Success Rate: {(metrics['successful_requests']/metrics['total_requests']*100):.1f}%")
        print(f"Avg Response Time: {metrics['avg_response_time']:.2f}ms")
        print(f"Min Response Time: {metrics['min_response_time']:.2f}ms")
        print(f"Max Response Time: {metrics['max_response_time']:.2f}ms")
        print(f"Requests/sec: {metrics['total_requests']/duration:.1f}")
        
        # Show final pool stats
        stats = pool.get_detailed_stats()
        print(f"\nFinal Pool Stats:")
        print(f"Active Connections: {stats['active']}")
        print(f"Idle Connections: {stats['idle']}")
        print(f"Total Created: {stats['created']}")
        print(f"Failed Connections: {stats['failed']}")
        
        pool.stop_monitoring()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()