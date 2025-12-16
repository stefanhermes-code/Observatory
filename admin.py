#!/usr/bin/env python3
"""
Admin App - PU Observatory Tool
Manages the entire Observatory process including scheduling and monitoring.
"""

import os
import sys
import json
from datetime import datetime
from configurator import Configurator
from generator import Generator


class Admin:
    """Administrative interface for managing the Observatory."""
    
    def __init__(self, config_dir="configs", report_dir="reports"):
        """Initialize the Admin interface."""
        self.configurator = Configurator(config_dir)
        self.generator = Generator(config_dir, report_dir)
        self.config_dir = config_dir
        self.report_dir = report_dir
    
    def status(self):
        """Display the status of the Observatory system."""
        print("\n" + "=" * 80)
        print("PU Observatory - System Status")
        print("=" * 80 + "\n")
        
        # Specifications status
        specs = self.configurator.list_specifications()
        print(f"Specifications: {len(specs)}")
        
        if specs:
            for spec_name in specs:
                try:
                    spec = self.configurator.load_specification(spec_name)
                    status = "ENABLED" if spec.get('enabled', True) else "DISABLED"
                    print(f"  [{status}] {spec_name}")
                    print(f"    Topics: {', '.join(spec['topics'])}")
                    print(f"    Sources: {', '.join(spec['sources'])}")
                    print(f"    Frequency: {spec['frequency']}")
                    print(f"    Format: {spec.get('output_format', 'text')}")
                except Exception as e:
                    print(f"  [ERROR] {spec_name}: {e}")
        else:
            print("  No specifications configured.")
        
        print()
        
        # Reports status
        if os.path.exists(self.report_dir):
            reports = [f for f in os.listdir(self.report_dir) if os.path.isfile(os.path.join(self.report_dir, f))]
            print(f"Reports generated: {len(reports)}")
            
            if reports:
                # Show last 5 reports
                reports.sort(reverse=True)
                print("  Recent reports:")
                for report in reports[:5]:
                    report_path = os.path.join(self.report_dir, report)
                    size = os.path.getsize(report_path)
                    print(f"    - {report} ({size} bytes)")
        else:
            print("Reports generated: 0")
        
        print("\n" + "=" * 80 + "\n")
    
    def run_scheduled_tasks(self):
        """Run all enabled scheduled tasks."""
        print("\n" + "=" * 80)
        print("PU Observatory - Running Scheduled Tasks")
        print("=" * 80 + "\n")
        
        specs = self.configurator.list_specifications()
        generated = 0
        
        for spec_name in specs:
            try:
                spec = self.configurator.load_specification(spec_name)
                
                if not spec.get('enabled', True):
                    print(f"[SKIP] {spec_name} - Disabled")
                    continue
                
                print(f"[RUN] {spec_name}")
                report_path = self.generator.generate_report(spec_name)
                
                if report_path:
                    generated += 1
                    print(f"[OK] Report generated: {report_path}")
                
            except Exception as e:
                print(f"[ERROR] {spec_name}: {e}")
        
        print(f"\nCompleted: {generated} reports generated")
        print("=" * 80 + "\n")
    
    def cleanup_old_reports(self, days=30):
        """Remove reports older than specified days."""
        if not os.path.exists(self.report_dir):
            print("No reports directory found.")
            return
        
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        removed = 0
        
        for filename in os.listdir(self.report_dir):
            filepath = os.path.join(self.report_dir, filename)
            if os.path.isfile(filepath):
                if os.path.getmtime(filepath) < cutoff:
                    os.remove(filepath)
                    removed += 1
                    print(f"Removed: {filename}")
        
        print(f"\nCleaned up {removed} old reports (older than {days} days)")
    
    def validate_configuration(self):
        """Validate all configurations."""
        print("\n" + "=" * 80)
        print("PU Observatory - Configuration Validation")
        print("=" * 80 + "\n")
        
        specs = self.configurator.list_specifications()
        valid = 0
        invalid = 0
        
        for spec_name in specs:
            try:
                spec = self.configurator.load_specification(spec_name)
                
                # Check required fields
                required_fields = ['name', 'topics', 'sources', 'frequency']
                missing = [field for field in required_fields if field not in spec]
                
                if missing:
                    print(f"[INVALID] {spec_name}")
                    print(f"  Missing fields: {', '.join(missing)}")
                    invalid += 1
                else:
                    # Check field types
                    errors = []
                    if not isinstance(spec['topics'], list) or not spec['topics']:
                        errors.append("topics must be a non-empty list")
                    if not isinstance(spec['sources'], list) or not spec['sources']:
                        errors.append("sources must be a non-empty list")
                    if spec['frequency'] not in ['daily', 'weekly', 'monthly', 'hourly']:
                        errors.append("frequency must be daily, weekly, monthly, or hourly")
                    
                    if errors:
                        print(f"[INVALID] {spec_name}")
                        for error in errors:
                            print(f"  - {error}")
                        invalid += 1
                    else:
                        print(f"[VALID] {spec_name}")
                        valid += 1
                
            except Exception as e:
                print(f"[ERROR] {spec_name}: {e}")
                invalid += 1
        
        print(f"\nValidation complete: {valid} valid, {invalid} invalid")
        print("=" * 80 + "\n")
    
    def create_example_config(self):
        """Create an example configuration."""
        example_path = os.path.join(self.config_dir, "example_config.yaml")
        
        if os.path.exists(example_path):
            print(f"Example configuration already exists: {example_path}")
            return
        
        self.configurator.create_specification(
            name="example_config",
            topics=["Technology", "Science", "Business"],
            sources=["TechCrunch", "HackerNews", "Reuters"],
            frequency="daily",
            output_format="html"
        )
        
        print(f"Example configuration created: {example_path}")


def main():
    """CLI interface for the Admin."""
    admin = Admin()
    
    if len(sys.argv) < 2:
        print("Usage: python admin.py [status|run|cleanup|validate|example]")
        print("\nCommands:")
        print("  status    - Display system status")
        print("  run       - Run all scheduled tasks")
        print("  cleanup   - Remove old reports (default: 30 days)")
        print("  validate  - Validate all configurations")
        print("  example   - Create an example configuration")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        admin.status()
    
    elif command == "run":
        admin.run_scheduled_tasks()
    
    elif command == "cleanup":
        days = 30
        if len(sys.argv) > 2:
            try:
                days = int(sys.argv[2])
            except ValueError:
                print("Invalid days parameter. Using default: 30")
        admin.cleanup_old_reports(days)
    
    elif command == "validate":
        admin.validate_configuration()
    
    elif command == "example":
        admin.create_example_config()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
