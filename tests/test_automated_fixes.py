#!/usr/bin/env python3
"""
Automated Fix Generator with Pattern Recognition and Code Templates
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import ast
import difflib
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FixPattern:
    """Fix pattern definition"""
    name: str
    error_pattern: str
    conditions: List[str]
    fix_template: str
    confidence: float
    tags: List[str]


@dataclass
class CodeFix:
    """Generated code fix"""
    file_path: str
    line_number: int
    original_code: str
    fixed_code: str
    pattern_name: str
    confidence: float
    explanation: str
    test_command: Optional[str] = None


class FixPatternLibrary:
    """Library of fix patterns"""
    
    def __init__(self):
        self.patterns: Dict[str, List[FixPattern]] = {
            "import_error": [
                FixPattern(
                    name="missing_import",
                    error_pattern=r"NameError: name '(\w+)' is not defined",
                    conditions=["module_exists", "not_imported"],
                    fix_template="import {module}",
                    confidence=0.9,
                    tags=["python", "import"]
                ),
                FixPattern(
                    name="circular_import",
                    error_pattern=r"ImportError: cannot import name .* \(most likely due to a circular import\)",
                    conditions=["circular_dependency"],
                    fix_template="# Move import inside function\ndef {function}():\n    from {module} import {name}",
                    confidence=0.8,
                    tags=["python", "import", "circular"]
                )
            ],
            "type_error": [
                FixPattern(
                    name="none_type_attribute",
                    error_pattern=r"AttributeError: 'NoneType' object has no attribute '(\w+)'",
                    conditions=["variable_can_be_none"],
                    fix_template="if {variable} is not None:\n    {variable}.{attribute}",
                    confidence=0.85,
                    tags=["python", "null_check"]
                ),
                FixPattern(
                    name="missing_await",
                    error_pattern=r"TypeError: object .* can't be used in 'await' expression",
                    conditions=["async_function", "missing_await"],
                    fix_template="await {function_call}",
                    confidence=0.9,
                    tags=["python", "async"]
                )
            ],
            "database_error": [
                FixPattern(
                    name="missing_migration",
                    error_pattern=r"relation \"(\w+)\" does not exist",
                    conditions=["table_in_model", "migration_missing"],
                    fix_template="-- Migration for {table}\nCREATE TABLE {table} (\n    id SERIAL PRIMARY KEY,\n    created_at TIMESTAMP DEFAULT NOW()\n);",
                    confidence=0.7,
                    tags=["sql", "migration"]
                ),
                FixPattern(
                    name="missing_index",
                    error_pattern=r"Slow query detected.*WHERE (\w+)",
                    conditions=["frequent_query", "no_index"],
                    fix_template="CREATE INDEX idx_{table}_{column} ON {table}({column});",
                    confidence=0.75,
                    tags=["sql", "performance"]
                )
            ],
            "api_error": [
                FixPattern(
                    name="missing_auth_header",
                    error_pattern=r"401.*Authorization header missing",
                    conditions=["api_requires_auth"],
                    fix_template="headers['Authorization'] = f'Bearer {{token}}'",
                    confidence=0.9,
                    tags=["api", "auth"]
                ),
                FixPattern(
                    name="cors_error",
                    error_pattern=r"CORS.*Access-Control-Allow-Origin",
                    conditions=["frontend_request", "cors_not_configured"],
                    fix_template="app.config['CORS_ORIGINS'] = ['http://localhost:3000']",
                    confidence=0.85,
                    tags=["api", "cors"]
                )
            ],
            "frontend_error": [
                FixPattern(
                    name="undefined_variable",
                    error_pattern=r"ReferenceError: (\w+) is not defined",
                    conditions=["javascript", "variable_not_declared"],
                    fix_template="const {variable} = {default_value};",
                    confidence=0.8,
                    tags=["javascript", "variable"]
                ),
                FixPattern(
                    name="missing_dependency",
                    error_pattern=r"Module not found: Can't resolve '(\w+)'",
                    conditions=["package_exists", "not_installed"],
                    fix_template="npm install {package}",
                    confidence=0.9,
                    tags=["javascript", "dependency"]
                )
            ]
        }
    
    def find_matching_patterns(self, error: str, context: Dict[str, Any]) -> List[FixPattern]:
        """Find patterns matching the error"""
        matches = []
        
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern.error_pattern, error):
                    # Check conditions
                    if self._check_conditions(pattern.conditions, context):
                        matches.append(pattern)
        
        return sorted(matches, key=lambda p: p.confidence, reverse=True)
    
    def _check_conditions(self, conditions: List[str], context: Dict[str, Any]) -> bool:
        """Check if all conditions are met"""
        # Simplified condition checking - in real implementation would be more sophisticated
        return True


class CodeAnalyzer:
    """Analyze code to understand context"""
    
    def analyze_python_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze Python file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            return {
                "imports": self._extract_imports(tree),
                "functions": self._extract_functions(tree),
                "classes": self._extract_classes(tree),
                "variables": self._extract_variables(tree),
                "async_functions": self._extract_async_functions(tree)
            }
        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {e}")
            return {}
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports
    
    def _extract_functions(self, tree: ast.AST) -> List[str]:
        """Extract function names"""
        return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    
    def _extract_classes(self, tree: ast.AST) -> List[str]:
        """Extract class names"""
        return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    
    def _extract_variables(self, tree: ast.AST) -> List[str]:
        """Extract variable names"""
        variables = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                variables.append(node.id)
        return list(set(variables))
    
    def _extract_async_functions(self, tree: ast.AST) -> List[str]:
        """Extract async function names"""
        return [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]


class AutomatedFixGenerator:
    """Generate automated fixes for errors"""
    
    def __init__(self):
        self.pattern_library = FixPatternLibrary()
        self.code_analyzer = CodeAnalyzer()
        self.generated_fixes: List[CodeFix] = []
    
    def generate_fixes(self, error_report: Dict[str, Any]) -> List[CodeFix]:
        """Generate fixes for errors in report"""
        fixes = []
        
        for test_type, results in error_report.items():
            if isinstance(results, dict) and "errors" in results:
                for error in results["errors"]:
                    fix = self._generate_fix_for_error(error, test_type)
                    if fix:
                        fixes.append(fix)
        
        self.generated_fixes = fixes
        return fixes
    
    def _generate_fix_for_error(self, error: Dict[str, Any], test_type: str) -> Optional[CodeFix]:
        """Generate fix for a specific error"""
        try:
            # Extract error details
            error_message = error.get("error", "")
            file_path = error.get("file", "")
            line_number = error.get("line", 0)
            
            # Analyze code context
            context = self._build_context(file_path, error, test_type)
            
            # Find matching patterns
            patterns = self.pattern_library.find_matching_patterns(error_message, context)
            
            if not patterns:
                return None
            
            # Use highest confidence pattern
            pattern = patterns[0]
            
            # Generate fix
            fixed_code = self._apply_fix_template(
                pattern.fix_template,
                error_message,
                context
            )
            
            # Get original code
            original_code = self._get_original_code(file_path, line_number)
            
            return CodeFix(
                file_path=file_path,
                line_number=line_number,
                original_code=original_code,
                fixed_code=fixed_code,
                pattern_name=pattern.name,
                confidence=pattern.confidence,
                explanation=f"Applied {pattern.name} pattern to fix {test_type} error",
                test_command=self._get_test_command(test_type, file_path)
            )
            
        except Exception as e:
            logger.error(f"Failed to generate fix: {e}")
            return None
    
    def _build_context(self, file_path: str, error: Dict[str, Any], test_type: str) -> Dict[str, Any]:
        """Build context for pattern matching"""
        context = {
            "test_type": test_type,
            "file_path": file_path,
            "error": error
        }
        
        # Add code analysis if Python file
        if file_path.endswith('.py'):
            context.update(self.code_analyzer.analyze_python_file(file_path))
        
        return context
    
    def _apply_fix_template(self, template: str, error_message: str, context: Dict[str, Any]) -> str:
        """Apply fix template with extracted values"""
        # Extract values from error message
        values = {}
        
        # Example: Extract module name from NameError
        match = re.search(r"NameError: name '(\w+)' is not defined", error_message)
        if match:
            values["module"] = match.group(1)
        
        # Example: Extract table name from database error
        match = re.search(r"relation \"(\w+)\" does not exist", error_message)
        if match:
            values["table"] = match.group(1)
        
        # Format template with values
        try:
            return template.format(**values)
        except KeyError:
            return template
    
    def _get_original_code(self, file_path: str, line_number: int) -> str:
        """Get original code at line"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                if 0 <= line_number - 1 < len(lines):
                    return lines[line_number - 1].rstrip()
        except:
            pass
        return ""
    
    def _get_test_command(self, test_type: str, file_path: str) -> str:
        """Get command to test the fix"""
        commands = {
            "api": f"pytest tests/test_api.py -v",
            "frontend": "npm test",
            "database": f"python -m pytest tests/test_database.py",
            "integration": "python tests/test_integration.py"
        }
        return commands.get(test_type, "python -m pytest")
    
    def apply_fixes(self, fixes: List[CodeFix], dry_run: bool = True) -> Dict[str, Any]:
        """Apply fixes to files"""
        results = {
            "applied": [],
            "skipped": [],
            "failed": []
        }
        
        for fix in fixes:
            try:
                if dry_run:
                    results["skipped"].append({
                        "file": fix.file_path,
                        "line": fix.line_number,
                        "reason": "dry run"
                    })
                else:
                    self._apply_fix_to_file(fix)
                    results["applied"].append({
                        "file": fix.file_path,
                        "line": fix.line_number,
                        "pattern": fix.pattern_name
                    })
            except Exception as e:
                results["failed"].append({
                    "file": fix.file_path,
                    "line": fix.line_number,
                    "error": str(e)
                })
        
        return results
    
    def _apply_fix_to_file(self, fix: CodeFix):
        """Apply a fix to a file"""
        with open(fix.file_path, 'r') as f:
            lines = f.readlines()
        
        # Apply fix at line
        if 0 <= fix.line_number - 1 < len(lines):
            lines[fix.line_number - 1] = fix.fixed_code + '\n'
        
        # Write back
        with open(fix.file_path, 'w') as f:
            f.writelines(lines)
    
    def generate_fix_report(self, fixes: List[CodeFix]) -> Dict[str, Any]:
        """Generate detailed fix report"""
        report = {
            "summary": {
                "total_fixes": len(fixes),
                "by_pattern": {},
                "by_confidence": {
                    "high": len([f for f in fixes if f.confidence >= 0.8]),
                    "medium": len([f for f in fixes if 0.6 <= f.confidence < 0.8]),
                    "low": len([f for f in fixes if f.confidence < 0.6])
                }
            },
            "fixes": []
        }
        
        # Count by pattern
        for fix in fixes:
            pattern = fix.pattern_name
            report["summary"]["by_pattern"][pattern] = report["summary"]["by_pattern"].get(pattern, 0) + 1
        
        # Add fix details
        for fix in fixes:
            report["fixes"].append({
                "file": fix.file_path,
                "line": fix.line_number,
                "pattern": fix.pattern_name,
                "confidence": fix.confidence,
                "original": fix.original_code,
                "fixed": fix.fixed_code,
                "explanation": fix.explanation,
                "test_command": fix.test_command,
                "diff": self._generate_diff(fix.original_code, fix.fixed_code)
            })
        
        return report
    
    def _generate_diff(self, original: str, fixed: str) -> str:
        """Generate diff between original and fixed code"""
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            fromfile="original",
            tofile="fixed"
        )
        return ''.join(diff)


def main():
    """Test the automated fix generator"""
    
    # Sample error report
    error_report = {
        "api": {
            "errors": [
                {
                    "error": "NameError: name 'json' is not defined",
                    "file": "app.py",
                    "line": 150,
                    "endpoint": "/api/recipes"
                },
                {
                    "error": "401 Unauthorized: Authorization header missing",
                    "file": "tests/test_api.py",
                    "line": 45,
                    "endpoint": "/api/user/profile"
                }
            ]
        },
        "database": {
            "errors": [
                {
                    "error": 'relation "user_stats" does not exist',
                    "file": "models.py",
                    "line": 200,
                    "query": "SELECT * FROM user_stats"
                }
            ]
        }
    }
    
    # Initialize generator
    generator = AutomatedFixGenerator()
    
    # Generate fixes
    logger.info("Generating fixes...")
    fixes = generator.generate_fixes(error_report)
    
    # Generate report
    fix_report = generator.generate_fix_report(fixes)
    
    # Display report
    print("\n" + "="*80)
    print("AUTOMATED FIX REPORT")
    print("="*80)
    print(f"\nTotal fixes generated: {fix_report['summary']['total_fixes']}")
    print(f"High confidence: {fix_report['summary']['by_confidence']['high']}")
    print(f"Medium confidence: {fix_report['summary']['by_confidence']['medium']}")
    print(f"Low confidence: {fix_report['summary']['by_confidence']['low']}")
    
    print("\nFixes by pattern:")
    for pattern, count in fix_report['summary']['by_pattern'].items():
        print(f"  - {pattern}: {count}")
    
    print("\nDetailed fixes:")
    for i, fix in enumerate(fix_report['fixes'], 1):
        print(f"\n{i}. {fix['file']}:{fix['line']} ({fix['pattern']})")
        print(f"   Confidence: {fix['confidence']:.0%}")
        print(f"   Original: {fix['original']}")
        print(f"   Fixed: {fix['fixed']}")
        print(f"   Test: {fix['test_command']}")
    
    # Save report
    output_file = "test_fixes_report.json"
    with open(output_file, 'w') as f:
        json.dump(fix_report, f, indent=2)
    
    logger.info(f"Fix report saved to {output_file}")


if __name__ == "__main__":
    main()