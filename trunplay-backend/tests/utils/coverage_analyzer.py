"""
Coverage gap analyzer.

Analyzes test coverage reports to identify untested code paths
and suggest test cases to improve coverage.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple


class CoverageAnalyzer:
    """Analyzes pytest-cov output to find coverage gaps."""

    def __init__(self, coverage_file: str = "coverage.json"):
        self.coverage_file = coverage_file
        self.report_data = None

    def load_report(self) -> bool:
        """Load coverage report from JSON file."""
        if not os.path.exists(self.coverage_file):
            print(f"Coverage file not found: {self.coverage_file}")
            print("Run: pytest --cov=src --cov-report=json")
            return False

        with open(self.coverage_file) as f:
            self.report_data = json.load(f)
        return True

    def find_untested_paths(self) -> List[Dict]:
        """Find files with missing coverage."""
        if not self.report_data:
            return []

        gaps = []
        files_data = self.report_data.get("files", {})

        for file_path, file_data in files_data.items():
            missing_lines = file_data.get("missing_lines", [])
            if missing_lines:
                summary = file_data.get("summary", {})
                gaps.append({
                    "file": file_path,
                    "missing_lines": missing_lines,
                    "coverage_percent": summary.get("percent_covered", 0),
                    "num_statements": summary.get("num_statements", 0),
                    "missing_count": len(missing_lines),
                })

        # Sort by coverage percentage (lowest first)
        return sorted(gaps, key=lambda x: x["coverage_percent"])

    def find_untested_branches(self) -> List[Dict]:
        """Find files with missing branch coverage."""
        if not self.report_data:
            return []

        gaps = []
        files_data = self.report_data.get("files", {})

        for file_path, file_data in files_data.items():
            missing_branches = file_data.get("missing_branches", [])
            if missing_branches:
                gaps.append({
                    "file": file_path,
                    "missing_branches": missing_branches,
                    "branch_count": len(missing_branches),
                })

        return sorted(gaps, key=lambda x: x["branch_count"], reverse=True)

    def get_priority_files(self, limit: int = 10) -> List[Dict]:
        """Get files that should be prioritized for testing."""
        gaps = self.find_untested_paths()

        # Prioritize:
        # 1. Core files (services, crud) with low coverage
        # 2. Files with most missing lines
        priority_patterns = ["services/", "crud.py", "api/"]

        def priority_score(gap: Dict) -> float:
            file_path = gap["file"]
            base_score = gap["missing_count"] * (100 - gap["coverage_percent"])

            # Boost score for important files
            for pattern in priority_patterns:
                if pattern in file_path:
                    base_score *= 2
                    break

            return base_score

        return sorted(gaps, key=priority_score, reverse=True)[:limit]

    def suggest_test_cases(self, file_path: str) -> List[str]:
        """Suggest test cases based on missing lines."""
        # This is a simplified suggestion - in practice would need
        # to parse the actual source code
        suggestions = []

        if "services/" in file_path:
            suggestions.extend([
                "Test service initialization",
                "Test normal operation flow",
                "Test error handling paths",
                "Test edge cases (empty input, max values)",
            ])
        elif "crud" in file_path:
            suggestions.extend([
                "Test create with valid data",
                "Test create with invalid data",
                "Test read existing record",
                "Test read non-existent record",
                "Test update partial fields",
                "Test delete and verify",
            ])
        elif "api/" in file_path:
            suggestions.extend([
                "Test successful request",
                "Test validation error (400)",
                "Test not found (404)",
                "Test server error handling (500)",
            ])

        return suggestions

    def generate_gap_report(self) -> str:
        """Generate a human-readable gap report."""
        if not self.load_report():
            return "Failed to load coverage report"

        lines = []
        lines.append("=" * 60)
        lines.append("COVERAGE GAP REPORT")
        lines.append("=" * 60)

        # Overall summary
        totals = self.report_data.get("totals", {})
        lines.append(f"\nOverall Coverage: {totals.get('percent_covered', 0):.1f}%")
        lines.append(f"Total Statements: {totals.get('num_statements', 0)}")
        lines.append(f"Missing Statements: {totals.get('missing_lines', 0)}")

        # Priority files
        lines.append("\n" + "-" * 60)
        lines.append("TOP PRIORITY FILES (need most attention)")
        lines.append("-" * 60)

        priority_files = self.get_priority_files(10)
        for i, gap in enumerate(priority_files, 1):
            lines.append(f"\n{i}. {gap['file']}")
            lines.append(f"   Coverage: {gap['coverage_percent']:.1f}%")
            lines.append(f"   Missing: {gap['missing_count']} lines")
            missing_preview = gap['missing_lines'][:5]
            lines.append(f"   Lines: {missing_preview}{'...' if len(gap['missing_lines']) > 5 else ''}")

        # Untested branches
        branches = self.find_untested_branches()
        if branches:
            lines.append("\n" + "-" * 60)
            lines.append("FILES WITH UNTESTED BRANCHES")
            lines.append("-" * 60)

            for gap in branches[:5]:
                lines.append(f"\n{gap['file']}")
                lines.append(f"   Untested branches: {gap['branch_count']}")

        # Summary
        gaps = self.find_untested_paths()
        lines.append("\n" + "=" * 60)
        lines.append(f"SUMMARY: {len(gaps)} files have coverage gaps")
        lines.append("=" * 60)

        return "\n".join(lines)

    def export_gaps_json(self, output_file: str = "coverage_gaps.json"):
        """Export gaps to JSON for further processing."""
        if not self.load_report():
            return

        gaps = {
            "priority_files": self.get_priority_files(20),
            "untested_branches": self.find_untested_branches(),
            "all_gaps": self.find_untested_paths(),
        }

        with open(output_file, "w") as f:
            json.dump(gaps, f, indent=2)

        print(f"Gaps exported to {output_file}")


def main():
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze test coverage gaps")
    parser.add_argument(
        "--coverage-file",
        default="coverage.json",
        help="Path to coverage JSON file"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export gaps to JSON file"
    )

    args = parser.parse_args()

    analyzer = CoverageAnalyzer(args.coverage_file)

    print(analyzer.generate_gap_report())

    if args.export:
        analyzer.export_gaps_json()


if __name__ == "__main__":
    main()
