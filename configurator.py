#!/usr/bin/env python3
"""
Configurator App - PU Observatory Tool
Allows users to create specifications for news reports.
"""

import json
import os
import yaml
from datetime import datetime


class Configurator:
    """Handles configuration specifications for news reports."""
    
    def __init__(self, config_dir="configs"):
        """Initialize the Configurator with a config directory."""
        self.config_dir = config_dir
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
    
    def create_specification(self, name, topics, sources, frequency, output_format="text"):
        """
        Create a new specification for a news report.
        
        Args:
            name: Name of the specification
            topics: List of topics to monitor
            sources: List of news sources to pull from
            frequency: How often to generate reports (daily, weekly, etc.)
            output_format: Output format (text, html, json)
        
        Returns:
            Path to the created specification file
        """
        spec = {
            "name": name,
            "topics": topics,
            "sources": sources,
            "frequency": frequency,
            "output_format": output_format,
            "created_at": datetime.now().isoformat(),
            "enabled": True
        }
        
        # Save as YAML for human readability
        spec_path = os.path.join(self.config_dir, f"{name}.yaml")
        with open(spec_path, 'w') as f:
            yaml.dump(spec, f, default_flow_style=False)
        
        print(f"Specification created: {spec_path}")
        return spec_path
    
    def load_specification(self, name):
        """Load a specification by name."""
        spec_path = os.path.join(self.config_dir, f"{name}.yaml")
        if not os.path.exists(spec_path):
            raise FileNotFoundError(f"Specification not found: {name}")
        
        with open(spec_path, 'r') as f:
            return yaml.safe_load(f)
    
    def list_specifications(self):
        """List all available specifications."""
        if not os.path.exists(self.config_dir):
            return []
        
        specs = []
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.yaml'):
                spec_name = filename[:-5]  # Remove .yaml extension
                specs.append(spec_name)
        return specs
    
    def update_specification(self, name, **kwargs):
        """Update an existing specification."""
        spec = self.load_specification(name)
        spec.update(kwargs)
        spec["updated_at"] = datetime.now().isoformat()
        
        spec_path = os.path.join(self.config_dir, f"{name}.yaml")
        with open(spec_path, 'w') as f:
            yaml.dump(spec, f, default_flow_style=False)
        
        print(f"Specification updated: {spec_path}")
        return spec_path
    
    def delete_specification(self, name):
        """Delete a specification."""
        spec_path = os.path.join(self.config_dir, f"{name}.yaml")
        if os.path.exists(spec_path):
            os.remove(spec_path)
            print(f"Specification deleted: {name}")
        else:
            raise FileNotFoundError(f"Specification not found: {name}")


def main():
    """CLI interface for the Configurator."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python configurator.py [create|list|update|delete]")
        sys.exit(1)
    
    configurator = Configurator()
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 6:
            print("Usage: python configurator.py create <name> <topics> <sources> <frequency>")
            print("Example: python configurator.py create 'tech-news' 'AI,ML,Cloud' 'TechCrunch,HackerNews' 'daily'")
            sys.exit(1)
        
        name = sys.argv[2]
        topics = sys.argv[3].split(',')
        sources = sys.argv[4].split(',')
        frequency = sys.argv[5]
        
        configurator.create_specification(name, topics, sources, frequency)
    
    elif command == "list":
        specs = configurator.list_specifications()
        print(f"Available specifications ({len(specs)}):")
        for spec in specs:
            print(f"  - {spec}")
    
    elif command == "update":
        if len(sys.argv) < 4:
            print("Usage: python configurator.py update <name> <field> <value>")
            sys.exit(1)
        
        name = sys.argv[2]
        field = sys.argv[3]
        value = sys.argv[4]
        
        # Parse value based on field type
        if field in ['topics', 'sources']:
            value = value.split(',')
        elif field == 'enabled':
            value = value.lower() == 'true'
        
        configurator.update_specification(name, **{field: value})
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: python configurator.py delete <name>")
            sys.exit(1)
        
        name = sys.argv[2]
        configurator.delete_specification(name)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
