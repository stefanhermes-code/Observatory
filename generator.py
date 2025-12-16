#!/usr/bin/env python3
"""
Generator App - PU Observatory Tool
Pulls news and generates reports based on specifications.
"""

import os
import json
from datetime import datetime
from configurator import Configurator


class NewsSource:
    """Base class for news sources."""
    
    def fetch_news(self, topics):
        """Fetch news for given topics."""
        raise NotImplementedError


class MockNewsSource(NewsSource):
    """Mock news source for demonstration."""
    
    def __init__(self, name):
        self.name = name
    
    def fetch_news(self, topics):
        """Fetch mock news articles."""
        articles = []
        for topic in topics:
            articles.append({
                "title": f"Latest developments in {topic}",
                "source": self.name,
                "topic": topic,
                "date": datetime.now().isoformat(),
                "summary": f"This is a summary of the latest news about {topic} from {self.name}.",
                "url": f"https://{self.name.lower().replace(' ', '')}.com/articles/{topic.lower()}"
            })
        return articles


class Generator:
    """Generates reports based on specifications."""
    
    def __init__(self, config_dir="configs", report_dir="reports"):
        """Initialize the Generator."""
        self.configurator = Configurator(config_dir)
        self.report_dir = report_dir
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
    
    def generate_report(self, spec_name):
        """
        Generate a report based on a specification.
        
        Args:
            spec_name: Name of the specification to use
        
        Returns:
            Path to the generated report
        """
        # Load specification
        spec = self.configurator.load_specification(spec_name)
        
        if not spec.get('enabled', True):
            print(f"Specification '{spec_name}' is disabled. Skipping.")
            return None
        
        print(f"Generating report for: {spec['name']}")
        
        # Pull news from sources
        all_articles = []
        for source_name in spec['sources']:
            source = MockNewsSource(source_name)
            articles = source.fetch_news(spec['topics'])
            all_articles.extend(articles)
        
        # Generate report based on format
        output_format = spec.get('output_format', 'text')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == 'json':
            report_path = self._generate_json_report(spec, all_articles, timestamp)
        elif output_format == 'html':
            report_path = self._generate_html_report(spec, all_articles, timestamp)
        else:
            report_path = self._generate_text_report(spec, all_articles, timestamp)
        
        print(f"Report generated: {report_path}")
        return report_path
    
    def _generate_text_report(self, spec, articles, timestamp):
        """Generate a text report."""
        report_path = os.path.join(self.report_dir, f"{spec['name']}_{timestamp}.txt")
        
        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(f"PU Observatory Report: {spec['name']}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Topics: {', '.join(spec['topics'])}\n")
            f.write(f"Sources: {', '.join(spec['sources'])}\n")
            f.write(f"Frequency: {spec['frequency']}\n\n")
            
            f.write("-" * 80 + "\n")
            f.write(f"Articles Found: {len(articles)}\n")
            f.write("-" * 80 + "\n\n")
            
            for i, article in enumerate(articles, 1):
                f.write(f"[{i}] {article['title']}\n")
                f.write(f"    Source: {article['source']}\n")
                f.write(f"    Topic: {article['topic']}\n")
                f.write(f"    Date: {article['date']}\n")
                f.write(f"    Summary: {article['summary']}\n")
                f.write(f"    URL: {article['url']}\n\n")
        
        return report_path
    
    def _generate_json_report(self, spec, articles, timestamp):
        """Generate a JSON report."""
        report_path = os.path.join(self.report_dir, f"{spec['name']}_{timestamp}.json")
        
        report = {
            "specification": spec['name'],
            "generated_at": datetime.now().isoformat(),
            "topics": spec['topics'],
            "sources": spec['sources'],
            "frequency": spec['frequency'],
            "article_count": len(articles),
            "articles": articles
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_path
    
    def _generate_html_report(self, spec, articles, timestamp):
        """Generate an HTML report."""
        report_path = os.path.join(self.report_dir, f"{spec['name']}_{timestamp}.html")
        
        with open(report_path, 'w') as f:
            f.write("<!DOCTYPE html>\n<html>\n<head>\n")
            f.write(f"<title>PU Observatory Report: {spec['name']}</title>\n")
            f.write("<style>\n")
            f.write("body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }\n")
            f.write(".header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }\n")
            f.write(".meta { background-color: white; padding: 15px; margin: 20px 0; border-radius: 5px; }\n")
            f.write(".article { background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #3498db; border-radius: 3px; }\n")
            f.write(".article h3 { margin-top: 0; color: #2c3e50; }\n")
            f.write(".article-meta { color: #7f8c8d; font-size: 0.9em; }\n")
            f.write("</style>\n</head>\n<body>\n")
            
            f.write("<div class='header'>\n")
            f.write(f"<h1>PU Observatory Report: {spec['name']}</h1>\n")
            f.write(f"<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
            f.write("</div>\n")
            
            f.write("<div class='meta'>\n")
            f.write(f"<p><strong>Topics:</strong> {', '.join(spec['topics'])}</p>\n")
            f.write(f"<p><strong>Sources:</strong> {', '.join(spec['sources'])}</p>\n")
            f.write(f"<p><strong>Frequency:</strong> {spec['frequency']}</p>\n")
            f.write(f"<p><strong>Articles Found:</strong> {len(articles)}</p>\n")
            f.write("</div>\n")
            
            for i, article in enumerate(articles, 1):
                f.write("<div class='article'>\n")
                f.write(f"<h3>{i}. {article['title']}</h3>\n")
                f.write(f"<p class='article-meta'>Source: {article['source']} | Topic: {article['topic']} | Date: {article['date']}</p>\n")
                f.write(f"<p>{article['summary']}</p>\n")
                f.write(f"<p><a href='{article['url']}' target='_blank'>Read more</a></p>\n")
                f.write("</div>\n")
            
            f.write("</body>\n</html>")
        
        return report_path
    
    def generate_all_reports(self):
        """Generate reports for all enabled specifications."""
        specs = self.configurator.list_specifications()
        reports = []
        
        for spec_name in specs:
            try:
                report_path = self.generate_report(spec_name)
                if report_path:
                    reports.append(report_path)
            except Exception as e:
                print(f"Error generating report for {spec_name}: {e}")
        
        return reports


def main():
    """CLI interface for the Generator."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python generator.py [generate|generate-all] [spec_name]")
        sys.exit(1)
    
    generator = Generator()
    command = sys.argv[1]
    
    if command == "generate":
        if len(sys.argv) < 3:
            print("Usage: python generator.py generate <spec_name>")
            sys.exit(1)
        
        spec_name = sys.argv[2]
        generator.generate_report(spec_name)
    
    elif command == "generate-all":
        reports = generator.generate_all_reports()
        print(f"\nGenerated {len(reports)} reports:")
        for report in reports:
            print(f"  - {report}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
