#!/usr/bin/env python3
"""
Advanced Reporting System with Executive Summary and Actionable Recommendations
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from dataclasses import dataclass
import pandas as pd
from jinja2 import Template
import markdown
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestMetrics:
    """Test execution metrics"""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration: float
    coverage: float
    performance_score: float
    stability_score: float


@dataclass
class Recommendation:
    """Actionable recommendation"""
    priority: str  # critical, high, medium, low
    category: str  # performance, security, reliability, maintainability
    title: str
    description: str
    impact: str
    effort: str  # low, medium, high
    steps: List[str]
    estimated_time: str
    related_issues: List[str]


class ReportGenerator:
    """Generate comprehensive test reports"""
    
    def __init__(self):
        self.report_dir = Path("test_reports")
        self.report_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now()
    
    def generate_executive_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary"""
        
        # Calculate overall metrics
        metrics = self._calculate_metrics(test_results)
        
        # Determine health status
        health_status = self._determine_health_status(metrics)
        
        # Generate trend analysis
        trends = self._analyze_trends(test_results)
        
        # Create summary
        summary = {
            "generated_at": self.timestamp.isoformat(),
            "overall_health": health_status,
            "key_metrics": {
                "test_success_rate": f"{metrics.passed / metrics.total_tests * 100:.1f}%",
                "code_coverage": f"{metrics.coverage:.1f}%",
                "performance_score": f"{metrics.performance_score:.1f}/100",
                "stability_score": f"{metrics.stability_score:.1f}/100",
                "total_execution_time": f"{metrics.duration:.2f}s"
            },
            "critical_issues": self._identify_critical_issues(test_results),
            "trends": trends,
            "risk_assessment": self._assess_risks(test_results, metrics),
            "business_impact": self._assess_business_impact(test_results)
        }
        
        return summary
    
    def _calculate_metrics(self, test_results: Dict[str, Any]) -> TestMetrics:
        """Calculate overall test metrics"""
        total = 0
        passed = 0
        failed = 0
        skipped = 0
        duration = 0.0
        
        for category, results in test_results.items():
            if isinstance(results, dict) and "summary" in results:
                summary = results["summary"]
                total += summary.get("total", 0)
                passed += summary.get("passed", 0)
                failed += summary.get("failed", 0)
                skipped += summary.get("skipped", 0)
                duration += summary.get("duration", 0)
        
        # Calculate scores
        coverage = test_results.get("coverage", {}).get("overall", 0)
        performance_score = self._calculate_performance_score(test_results)
        stability_score = self._calculate_stability_score(test_results)
        
        return TestMetrics(
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=duration,
            coverage=coverage,
            performance_score=performance_score,
            stability_score=stability_score
        )
    
    def _determine_health_status(self, metrics: TestMetrics) -> str:
        """Determine overall health status"""
        success_rate = metrics.passed / metrics.total_tests if metrics.total_tests > 0 else 0
        
        if success_rate >= 0.95 and metrics.coverage >= 80:
            return "healthy"
        elif success_rate >= 0.85 and metrics.coverage >= 70:
            return "good"
        elif success_rate >= 0.70:
            return "warning"
        else:
            return "critical"
    
    def _analyze_trends(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends from historical data"""
        # In production, would load historical data
        return {
            "test_success_trend": "improving",  # improving, stable, declining
            "performance_trend": "stable",
            "coverage_trend": "improving",
            "failure_patterns": self._identify_failure_patterns(test_results)
        }
    
    def _identify_critical_issues(self, test_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify critical issues"""
        critical_issues = []
        
        # Check for security vulnerabilities
        if "security" in test_results:
            for vuln in test_results["security"].get("vulnerabilities", []):
                if vuln.get("severity") == "critical":
                    critical_issues.append({
                        "type": "security",
                        "title": vuln.get("title"),
                        "severity": "critical",
                        "affected_component": vuln.get("component")
                    })
        
        # Check for performance issues
        if "performance" in test_results:
            for metric in test_results["performance"].get("metrics", []):
                if metric.get("status") == "failed":
                    critical_issues.append({
                        "type": "performance",
                        "title": f"Performance degradation in {metric.get('endpoint')}",
                        "severity": "high",
                        "impact": metric.get("impact")
                    })
        
        # Check for broken core functionality
        if "api" in test_results:
            for error in test_results["api"].get("errors", []):
                if "authentication" in error.get("endpoint", "").lower():
                    critical_issues.append({
                        "type": "functionality",
                        "title": "Authentication system failure",
                        "severity": "critical",
                        "endpoint": error.get("endpoint")
                    })
        
        return critical_issues
    
    def _assess_risks(self, test_results: Dict[str, Any], metrics: TestMetrics) -> Dict[str, Any]:
        """Assess project risks"""
        risks = {
            "deployment_risk": "low",
            "security_risk": "medium",
            "performance_risk": "low",
            "user_impact_risk": "medium"
        }
        
        # Adjust based on metrics
        if metrics.passed / metrics.total_tests < 0.8:
            risks["deployment_risk"] = "high"
        
        if "security" in test_results and test_results["security"].get("vulnerabilities"):
            risks["security_risk"] = "high"
        
        if metrics.performance_score < 70:
            risks["performance_risk"] = "high"
        
        return risks
    
    def _assess_business_impact(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess business impact of issues"""
        return {
            "user_experience": self._assess_ux_impact(test_results),
            "revenue_impact": self._assess_revenue_impact(test_results),
            "brand_risk": self._assess_brand_risk(test_results),
            "compliance_risk": self._assess_compliance_risk(test_results)
        }
    
    def _assess_ux_impact(self, test_results: Dict[str, Any]) -> str:
        """Assess user experience impact"""
        frontend_failures = test_results.get("frontend", {}).get("summary", {}).get("failed", 0)
        api_failures = test_results.get("api", {}).get("summary", {}).get("failed", 0)
        
        if frontend_failures > 5 or api_failures > 10:
            return "high"
        elif frontend_failures > 2 or api_failures > 5:
            return "medium"
        return "low"
    
    def _assess_revenue_impact(self, test_results: Dict[str, Any]) -> str:
        """Assess potential revenue impact"""
        # Check for failures in critical business flows
        critical_endpoints = ["/api/checkout", "/api/payment", "/api/subscription"]
        
        api_errors = test_results.get("api", {}).get("errors", [])
        critical_failures = [e for e in api_errors if any(ep in e.get("endpoint", "") for ep in critical_endpoints)]
        
        if critical_failures:
            return "high"
        return "low"
    
    def _assess_brand_risk(self, test_results: Dict[str, Any]) -> str:
        """Assess brand reputation risk"""
        security_vulns = test_results.get("security", {}).get("vulnerabilities", [])
        critical_vulns = [v for v in security_vulns if v.get("severity") == "critical"]
        
        if critical_vulns:
            return "high"
        return "medium" if security_vulns else "low"
    
    def _assess_compliance_risk(self, test_results: Dict[str, Any]) -> str:
        """Assess compliance risk"""
        # Check for data protection and privacy issues
        compliance_issues = []
        
        # Check security scan results
        if "security" in test_results:
            for vuln in test_results["security"].get("vulnerabilities", []):
                if "data" in vuln.get("title", "").lower() or "privacy" in vuln.get("title", "").lower():
                    compliance_issues.append(vuln)
        
        return "high" if compliance_issues else "low"
    
    def _calculate_performance_score(self, test_results: Dict[str, Any]) -> float:
        """Calculate overall performance score"""
        if "performance" not in test_results:
            return 100.0
        
        metrics = test_results["performance"].get("metrics", [])
        if not metrics:
            return 100.0
        
        passed_metrics = [m for m in metrics if m.get("status") == "passed"]
        return (len(passed_metrics) / len(metrics)) * 100
    
    def _calculate_stability_score(self, test_results: Dict[str, Any]) -> float:
        """Calculate stability score"""
        # Based on flaky tests and intermittent failures
        total_tests = 0
        stable_tests = 0
        
        for category, results in test_results.items():
            if isinstance(results, dict) and "tests" in results:
                for test in results["tests"]:
                    total_tests += 1
                    if not test.get("flaky", False):
                        stable_tests += 1
        
        return (stable_tests / total_tests * 100) if total_tests > 0 else 100.0
    
    def _identify_failure_patterns(self, test_results: Dict[str, Any]) -> List[str]:
        """Identify common failure patterns"""
        patterns = []
        
        # Analyze error messages
        all_errors = []
        for category, results in test_results.items():
            if isinstance(results, dict) and "errors" in results:
                all_errors.extend(results["errors"])
        
        # Common patterns
        if any("timeout" in str(e).lower() for e in all_errors):
            patterns.append("Timeout issues detected")
        
        if any("connection" in str(e).lower() for e in all_errors):
            patterns.append("Connection/Network issues")
        
        if any("permission" in str(e).lower() or "auth" in str(e).lower() for e in all_errors):
            patterns.append("Authentication/Authorization failures")
        
        return patterns
    
    def generate_recommendations(self, test_results: Dict[str, Any], executive_summary: Dict[str, Any]) -> List[Recommendation]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Performance recommendations
        if executive_summary["key_metrics"]["performance_score"].rstrip("/100") < "80":
            recommendations.append(Recommendation(
                priority="high",
                category="performance",
                title="Optimize Application Performance",
                description="Performance tests show significant degradation in response times",
                impact="User experience and conversion rates",
                effort="medium",
                steps=[
                    "Profile slow endpoints identified in performance tests",
                    "Implement caching for frequently accessed data",
                    "Optimize database queries with proper indexing",
                    "Consider implementing CDN for static assets"
                ],
                estimated_time="2-3 days",
                related_issues=["Slow API responses", "Database query timeouts"]
            ))
        
        # Security recommendations
        critical_issues = executive_summary.get("critical_issues", [])
        security_issues = [i for i in critical_issues if i.get("type") == "security"]
        
        if security_issues:
            recommendations.append(Recommendation(
                priority="critical",
                category="security",
                title="Address Critical Security Vulnerabilities",
                description="Critical security vulnerabilities detected that could lead to data breaches",
                impact="Data security and compliance",
                effort="high",
                steps=[
                    "Apply security patches for identified vulnerabilities",
                    "Update vulnerable dependencies",
                    "Implement security headers and CSP",
                    "Conduct security audit"
                ],
                estimated_time="1-2 days",
                related_issues=[issue["title"] for issue in security_issues]
            ))
        
        # Test coverage recommendations
        coverage = float(executive_summary["key_metrics"]["code_coverage"].rstrip("%"))
        if coverage < 80:
            recommendations.append(Recommendation(
                priority="medium",
                category="maintainability",
                title="Improve Test Coverage",
                description=f"Current test coverage is {coverage}%, below recommended 80%",
                impact="Code quality and bug prevention",
                effort="medium",
                steps=[
                    "Identify untested critical paths",
                    "Add unit tests for core business logic",
                    "Implement integration tests for API endpoints",
                    "Set up coverage gates in CI/CD"
                ],
                estimated_time="3-5 days",
                related_issues=["Low test coverage", "Untested code paths"]
            ))
        
        # Stability recommendations
        if executive_summary["trends"]["failure_patterns"]:
            recommendations.append(Recommendation(
                priority="high",
                category="reliability",
                title="Address Test Instability",
                description="Recurring failure patterns indicate system instability",
                impact="Development velocity and reliability",
                effort="medium",
                steps=[
                    "Fix flaky tests identified in the report",
                    "Implement retry mechanisms for network calls",
                    "Add proper error handling and logging",
                    "Set up monitoring for production issues"
                ],
                estimated_time="2-3 days",
                related_issues=executive_summary["trends"]["failure_patterns"]
            ))
        
        return sorted(recommendations, key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}[r.priority])
    
    def generate_visualizations(self, test_results: Dict[str, Any], executive_summary: Dict[str, Any]) -> List[str]:
        """Generate visualization charts"""
        charts = []
        
        # Test results pie chart
        chart_path = self._create_test_results_chart(test_results)
        if chart_path:
            charts.append(chart_path)
        
        # Performance trends
        chart_path = self._create_performance_chart(test_results)
        if chart_path:
            charts.append(chart_path)
        
        # Coverage heatmap
        chart_path = self._create_coverage_heatmap(test_results)
        if chart_path:
            charts.append(chart_path)
        
        # Risk matrix
        chart_path = self._create_risk_matrix(executive_summary)
        if chart_path:
            charts.append(chart_path)
        
        return charts
    
    def _create_test_results_chart(self, test_results: Dict[str, Any]) -> Optional[str]:
        """Create test results pie chart"""
        try:
            metrics = self._calculate_metrics(test_results)
            
            # Create pie chart
            fig, ax = plt.subplots(figsize=(8, 6))
            
            sizes = [metrics.passed, metrics.failed, metrics.skipped]
            labels = ['Passed', 'Failed', 'Skipped']
            colors = ['#4CAF50', '#F44336', '#FFC107']
            
            # Filter out zero values
            filtered_data = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]
            if not filtered_data:
                return None
            
            sizes, labels, colors = zip(*filtered_data)
            
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            
            plt.title('Test Results Distribution', fontsize=16, fontweight='bold')
            
            # Save chart
            chart_path = self.report_dir / f"test_results_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"Failed to create test results chart: {e}")
            return None
    
    def _create_performance_chart(self, test_results: Dict[str, Any]) -> Optional[str]:
        """Create performance metrics chart"""
        try:
            if "performance" not in test_results:
                return None
            
            metrics = test_results["performance"].get("metrics", [])
            if not metrics:
                return None
            
            # Prepare data
            endpoints = [m["endpoint"] for m in metrics[:10]]  # Top 10
            response_times = [m["response_time"] for m in metrics[:10]]
            thresholds = [m["threshold"] for m in metrics[:10]]
            
            # Create bar chart
            fig, ax = plt.subplots(figsize=(12, 6))
            
            x = range(len(endpoints))
            width = 0.35
            
            bars1 = ax.bar([i - width/2 for i in x], response_times, width, label='Actual', color='#2196F3')
            bars2 = ax.bar([i + width/2 for i in x], thresholds, width, label='Threshold', color='#FF9800')
            
            ax.set_xlabel('Endpoints')
            ax.set_ylabel('Response Time (ms)')
            ax.set_title('API Performance Metrics', fontsize=16, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels([e.split('/')[-1] for e in endpoints], rotation=45, ha='right')
            ax.legend()
            
            # Add value labels
            for bar in bars1:
                height = bar.get_height()
                ax.annotate(f'{height:.0f}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom',
                           fontsize=8)
            
            plt.tight_layout()
            
            # Save chart
            chart_path = self.report_dir / f"performance_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"Failed to create performance chart: {e}")
            return None
    
    def _create_coverage_heatmap(self, test_results: Dict[str, Any]) -> Optional[str]:
        """Create test coverage heatmap"""
        try:
            coverage_data = test_results.get("coverage", {}).get("by_module", {})
            if not coverage_data:
                return None
            
            # Prepare data
            modules = list(coverage_data.keys())[:15]  # Top 15 modules
            coverage_values = [coverage_data[m] for m in modules]
            
            # Create horizontal bar chart with color coding
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # Color based on coverage
            colors = ['#4CAF50' if c >= 80 else '#FFC107' if c >= 60 else '#F44336' for c in coverage_values]
            
            bars = ax.barh(modules, coverage_values, color=colors)
            
            # Add percentage labels
            for bar, value in zip(bars, coverage_values):
                ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                       f'{value:.1f}%', ha='left', va='center')
            
            ax.set_xlabel('Coverage %')
            ax.set_title('Code Coverage by Module', fontsize=16, fontweight='bold')
            ax.set_xlim(0, 105)
            
            # Add legend
            legend_elements = [
                mpatches.Patch(color='#4CAF50', label='Good (≥80%)'),
                mpatches.Patch(color='#FFC107', label='Fair (60-79%)'),
                mpatches.Patch(color='#F44336', label='Poor (<60%)')
            ]
            ax.legend(handles=legend_elements, loc='lower right')
            
            plt.tight_layout()
            
            # Save chart
            chart_path = self.report_dir / f"coverage_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"Failed to create coverage heatmap: {e}")
            return None
    
    def _create_risk_matrix(self, executive_summary: Dict[str, Any]) -> Optional[str]:
        """Create risk assessment matrix"""
        try:
            risks = executive_summary.get("risk_assessment", {})
            
            # Define risk positions (impact, likelihood)
            risk_positions = {
                "deployment_risk": (3, 2),
                "security_risk": (4, 3),
                "performance_risk": (2, 2),
                "user_impact_risk": (3, 3)
            }
            
            # Create scatter plot
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # Set up grid
            ax.set_xlim(0, 5)
            ax.set_ylim(0, 5)
            ax.set_xlabel('Likelihood', fontsize=12)
            ax.set_ylabel('Impact', fontsize=12)
            ax.set_title('Risk Assessment Matrix', fontsize=16, fontweight='bold')
            
            # Add grid
            ax.grid(True, alpha=0.3)
            
            # Add risk zones
            ax.axhspan(0, 2, 0, 2, alpha=0.2, color='green')
            ax.axhspan(2, 3.5, 0, 3.5, alpha=0.2, color='yellow')
            ax.axhspan(3.5, 5, 3.5, 5, alpha=0.2, color='red')
            
            # Plot risks
            for risk_name, (impact, likelihood) in risk_positions.items():
                risk_level = risks.get(risk_name, "medium")
                color = {'low': 'green', 'medium': 'orange', 'high': 'red'}[risk_level]
                
                ax.scatter(likelihood, impact, s=500, c=color, alpha=0.7, edgecolors='black')
                ax.annotate(risk_name.replace('_', '\n'), 
                           (likelihood, impact), 
                           ha='center', va='center',
                           fontsize=10, fontweight='bold')
            
            # Add labels
            ax.text(1, 4.5, 'Low Risk', ha='center', fontsize=12, color='green', fontweight='bold')
            ax.text(2.5, 4.5, 'Medium Risk', ha='center', fontsize=12, color='orange', fontweight='bold')
            ax.text(4, 4.5, 'High Risk', ha='center', fontsize=12, color='red', fontweight='bold')
            
            plt.tight_layout()
            
            # Save chart
            chart_path = self.report_dir / f"risk_matrix_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"Failed to create risk matrix: {e}")
            return None
    
    def generate_html_report(self, test_results: Dict[str, Any], executive_summary: Dict[str, Any], 
                           recommendations: List[Recommendation], charts: List[str]) -> str:
        """Generate HTML report"""
        
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {{ timestamp }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 3px solid #2196F3; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        h3 { color: #666; }
        .summary { background-color: #f0f7ff; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .metric { display: inline-block; margin: 10px 20px; }
        .metric-value { font-size: 24px; font-weight: bold; color: #2196F3; }
        .metric-label { font-size: 14px; color: #666; }
        .status-healthy { color: #4CAF50; }
        .status-good { color: #8BC34A; }
        .status-warning { color: #FFC107; }
        .status-critical { color: #F44336; }
        .issue { background-color: #ffebee; padding: 15px; margin: 10px 0; border-left: 4px solid #F44336; }
        .recommendation { background-color: #e3f2fd; padding: 15px; margin: 10px 0; border-left: 4px solid #2196F3; }
        .priority-critical { border-left-color: #F44336; }
        .priority-high { border-left-color: #FF9800; }
        .priority-medium { border-left-color: #FFC107; }
        .priority-low { border-left-color: #4CAF50; }
        .chart { margin: 20px 0; text-align: center; }
        .chart img { max-width: 100%; height: auto; border: 1px solid #ddd; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f5f5f5; font-weight: bold; }
        .risk-high { background-color: #ffcdd2; }
        .risk-medium { background-color: #fff3cd; }
        .risk-low { background-color: #c8e6c9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Test Execution Report</h1>
        <p>Generated on {{ timestamp }}</p>
        
        <div class="summary">
            <h2>Executive Summary</h2>
            <p>Overall System Health: <span class="status-{{ health_status }}">{{ health_status|upper }}</span></p>
            
            <div class="metrics">
                {% for label, value in metrics.items() %}
                <div class="metric">
                    <div class="metric-value">{{ value }}</div>
                    <div class="metric-label">{{ label|replace('_', ' ')|title }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        {% if critical_issues %}
        <div class="issues">
            <h2>Critical Issues</h2>
            {% for issue in critical_issues %}
            <div class="issue">
                <h3>{{ issue.title }}</h3>
                <p><strong>Type:</strong> {{ issue.type }}</p>
                <p><strong>Severity:</strong> {{ issue.severity }}</p>
                {% if issue.affected_component %}
                <p><strong>Component:</strong> {{ issue.affected_component }}</p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="recommendations">
            <h2>Recommendations</h2>
            {% for rec in recommendations %}
            <div class="recommendation priority-{{ rec.priority }}">
                <h3>{{ rec.title }}</h3>
                <p><strong>Priority:</strong> {{ rec.priority|upper }}</p>
                <p><strong>Category:</strong> {{ rec.category }}</p>
                <p>{{ rec.description }}</p>
                <p><strong>Impact:</strong> {{ rec.impact }}</p>
                <p><strong>Effort:</strong> {{ rec.effort }} ({{ rec.estimated_time }})</p>
                <h4>Steps:</h4>
                <ol>
                    {% for step in rec.steps %}
                    <li>{{ step }}</li>
                    {% endfor %}
                </ol>
            </div>
            {% endfor %}
        </div>
        
        <div class="risk-assessment">
            <h2>Risk Assessment</h2>
            <table>
                <tr>
                    <th>Risk Area</th>
                    <th>Level</th>
                    <th>Description</th>
                </tr>
                {% for risk, level in risks.items() %}
                <tr class="risk-{{ level }}">
                    <td>{{ risk|replace('_', ' ')|title }}</td>
                    <td>{{ level|upper }}</td>
                    <td>{{ risk_descriptions[risk] }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="charts">
            <h2>Visualizations</h2>
            {% for chart in charts %}
            <div class="chart">
                <img src="{{ chart }}" alt="Test visualization">
            </div>
            {% endfor %}
        </div>
        
        <div class="detailed-results">
            <h2>Detailed Test Results</h2>
            <table>
                <tr>
                    <th>Test Category</th>
                    <th>Total</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Success Rate</th>
                </tr>
                {% for category, results in test_details.items() %}
                <tr>
                    <td>{{ category|title }}</td>
                    <td>{{ results.total }}</td>
                    <td>{{ results.passed }}</td>
                    <td>{{ results.failed }}</td>
                    <td>{{ "%.1f"|format(results.success_rate) }}%</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
        """
        
        # Prepare template data
        template_data = {
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "health_status": executive_summary["overall_health"],
            "metrics": executive_summary["key_metrics"],
            "critical_issues": executive_summary["critical_issues"],
            "recommendations": recommendations,
            "risks": executive_summary["risk_assessment"],
            "risk_descriptions": {
                "deployment_risk": "Risk of deployment failures or rollback requirements",
                "security_risk": "Risk of security vulnerabilities or data breaches",
                "performance_risk": "Risk of performance degradation affecting users",
                "user_impact_risk": "Risk of negative impact on user experience"
            },
            "charts": charts,
            "test_details": self._prepare_test_details(test_results)
        }
        
        # Render template
        template = Template(html_template)
        html_content = template.render(**template_data)
        
        # Save HTML report
        report_path = self.report_dir / f"test_report_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        return str(report_path)
    
    def _prepare_test_details(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare test details for report"""
        details = {}
        
        for category, results in test_results.items():
            if isinstance(results, dict) and "summary" in results:
                summary = results["summary"]
                total = summary.get("total", 0)
                passed = summary.get("passed", 0)
                failed = summary.get("failed", 0)
                
                details[category] = {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "success_rate": (passed / total * 100) if total > 0 else 0
                }
        
        return details
    
    def generate_markdown_report(self, test_results: Dict[str, Any], executive_summary: Dict[str, Any],
                               recommendations: List[Recommendation]) -> str:
        """Generate markdown report for GitHub/GitLab"""
        
        md_content = f"""# Test Execution Report

Generated: {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}

## Executive Summary

**Overall Health:** {executive_summary["overall_health"].upper()}

### Key Metrics
- **Test Success Rate:** {executive_summary["key_metrics"]["test_success_rate"]}
- **Code Coverage:** {executive_summary["key_metrics"]["code_coverage"]}
- **Performance Score:** {executive_summary["key_metrics"]["performance_score"]}
- **Stability Score:** {executive_summary["key_metrics"]["stability_score"]}
- **Execution Time:** {executive_summary["key_metrics"]["total_execution_time"]}

### Risk Assessment
"""
        
        for risk, level in executive_summary["risk_assessment"].items():
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[level]
            md_content += f"- **{risk.replace('_', ' ').title()}:** {emoji} {level.upper()}\n"
        
        if executive_summary["critical_issues"]:
            md_content += "\n## Critical Issues\n\n"
            for issue in executive_summary["critical_issues"]:
                md_content += f"### ⚠️ {issue['title']}\n"
                md_content += f"- **Type:** {issue['type']}\n"
                md_content += f"- **Severity:** {issue['severity']}\n\n"
        
        md_content += "\n## Recommendations\n\n"
        for i, rec in enumerate(recommendations, 1):
            priority_emoji = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "📋",
                "low": "💡"
            }[rec.priority]
            
            md_content += f"### {i}. {priority_emoji} {rec.title}\n\n"
            md_content += f"**Priority:** {rec.priority.upper()} | "
            md_content += f"**Category:** {rec.category} | "
            md_content += f"**Effort:** {rec.effort} ({rec.estimated_time})\n\n"
            md_content += f"{rec.description}\n\n"
            md_content += "**Steps:**\n"
            for step in rec.steps:
                md_content += f"- {step}\n"
            md_content += "\n"
        
        # Save markdown report
        report_path = self.report_dir / f"test_report_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_path, 'w') as f:
            f.write(md_content)
        
        return str(report_path)


def main():
    """Test the reporting system"""
    
    # Sample test results
    test_results = {
        "api": {
            "summary": {"total": 58, "passed": 52, "failed": 6, "skipped": 0, "duration": 45.2},
            "errors": [
                {"endpoint": "/api/authentication", "error": "401 Unauthorized", "severity": "critical"}
            ]
        },
        "frontend": {
            "summary": {"total": 35, "passed": 30, "failed": 5, "skipped": 0, "duration": 120.5}
        },
        "performance": {
            "summary": {"total": 20, "passed": 15, "failed": 5, "skipped": 0},
            "metrics": [
                {"endpoint": "/api/recipes", "response_time": 250, "threshold": 200, "status": "failed"},
                {"endpoint": "/api/users", "response_time": 150, "threshold": 200, "status": "passed"}
            ]
        },
        "security": {
            "vulnerabilities": [
                {"title": "SQL Injection", "severity": "critical", "component": "database"}
            ]
        },
        "coverage": {
            "overall": 75.5,
            "by_module": {
                "app.py": 85.2,
                "models.py": 92.1,
                "utils.py": 65.3,
                "api/routes.py": 78.9
            }
        }
    }
    
    # Initialize report generator
    generator = ReportGenerator()
    
    # Generate executive summary
    logger.info("Generating executive summary...")
    executive_summary = generator.generate_executive_summary(test_results)
    
    # Generate recommendations
    logger.info("Generating recommendations...")
    recommendations = generator.generate_recommendations(test_results, executive_summary)
    
    # Generate visualizations
    logger.info("Generating visualizations...")
    charts = generator.generate_visualizations(test_results, executive_summary)
    
    # Generate HTML report
    logger.info("Generating HTML report...")
    html_report = generator.generate_html_report(test_results, executive_summary, recommendations, charts)
    
    # Generate Markdown report
    logger.info("Generating Markdown report...")
    md_report = generator.generate_markdown_report(test_results, executive_summary, recommendations)
    
    print(f"\nReports generated:")
    print(f"- HTML: {html_report}")
    print(f"- Markdown: {md_report}")
    print(f"- Charts: {len(charts)} visualizations created")


if __name__ == "__main__":
    main()