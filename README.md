# Observatory
PU Observatory Tool - A comprehensive news monitoring and report generation system

## Overview

The PU Observatory is a tool that pulls news from various sources and generates customized reports based on user specifications. The system consists of three main components:

1. **Configurator** - Create and manage specifications for news reports
2. **Generator** - Pull news and generate reports based on specifications
3. **Admin** - Manage the entire Observatory process

## Installation

### Prerequisites
- Python 3.7 or higher

### Setup

1. Clone the repository:
```bash
git clone https://github.com/stefanhermes-code/Observatory.git
cd Observatory
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Components

### 1. Configurator App

The Configurator allows users to create specifications for news reports.

**Usage:**

```bash
# Create a new specification
python configurator.py create "tech-news" "AI,ML,Cloud" "TechCrunch,HackerNews" "daily"

# List all specifications
python configurator.py list

# Update a specification
python configurator.py update "tech-news" frequency weekly

# Delete a specification
python configurator.py delete "tech-news"
```

**Specification Fields:**
- `name`: Unique name for the specification
- `topics`: Comma-separated list of topics to monitor
- `sources`: Comma-separated list of news sources
- `frequency`: How often to generate reports (daily, weekly, monthly, hourly)
- `output_format`: Output format (text, html, json)

### 2. Generator App

The Generator pulls news from sources and generates reports based on specifications.

**Usage:**

```bash
# Generate a report for a specific specification
python generator.py generate "tech-news"

# Generate reports for all enabled specifications
python generator.py generate-all
```

**Output Formats:**
- **Text** (.txt): Simple text-based report
- **HTML** (.html): Styled HTML report with links
- **JSON** (.json): Structured data format

Reports are saved in the `reports/` directory with timestamps.

### 3. Admin App

The Admin app manages the entire Observatory system.

**Usage:**

```bash
# Display system status
python admin.py status

# Run all scheduled tasks
python admin.py run

# Clean up old reports (default: 30 days)
python admin.py cleanup
python admin.py cleanup 60  # Keep reports for 60 days

# Validate all configurations
python admin.py validate

# Create an example configuration
python admin.py example
```

## Quick Start

1. Create an example configuration:
```bash
python admin.py example
```

2. Check system status:
```bash
python admin.py status
```

3. Generate a report:
```bash
python generator.py generate "example_config"
```

4. View the generated report in the `reports/` directory.

## Directory Structure

```
Observatory/
├── configurator.py      # Configurator app
├── generator.py         # Generator app
├── admin.py            # Admin app
├── requirements.txt    # Python dependencies
├── configs/           # Configuration files (created automatically)
│   └── *.yaml        # Specification files
└── reports/          # Generated reports (created automatically)
    └── *.txt/html/json
```

## Workflow

1. **Configure**: Use the Configurator to create specifications
2. **Generate**: Use the Generator to create reports based on specifications
3. **Manage**: Use the Admin to monitor and manage the system

## Advanced Usage

### Programmatic Access

All three components can be imported and used programmatically:

```python
from configurator import Configurator
from generator import Generator
from admin import Admin

# Create a specification
config = Configurator()
config.create_specification(
    name="my-report",
    topics=["AI", "Machine Learning"],
    sources=["TechCrunch", "MIT News"],
    frequency="daily",
    output_format="html"
)

# Generate a report
gen = Generator()
report_path = gen.generate_report("my-report")

# Check system status
admin = Admin()
admin.status()
```

## Configuration Files

Specifications are stored as YAML files in the `configs/` directory:

```yaml
name: tech-news
topics:
  - AI
  - ML
  - Cloud
sources:
  - TechCrunch
  - HackerNews
frequency: daily
output_format: html
created_at: '2025-12-16T02:24:00'
enabled: true
```

## License

This project is part of the PU Observatory system.
