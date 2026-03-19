"""
pos_analysis/shared — POS-Agnostic Analysis & Export
=====================================================
Shared analysis and reporting modules used across all POS adapters.
These modules are independent of any specific POS system.

Modules:
    menu_engineering   — BCG-style menu matrix analysis
    cross_domain       — Multi-domain insight generation
    exporters          — Report compilation and JSON export

Import example::

    from pos_analysis.shared.menu_engineering import MenuEngineeringAnalyzer
    from pos_analysis.shared.cross_domain import generate_cross_domain_insights
    from pos_analysis.shared.exporters import ReportExporter

    menu_analyzer = MenuEngineeringAnalyzer(items=data.items)
    menu_results = menu_analyzer.run_all()

    insights = generate_cross_domain_insights(all_results)

    exporter = ReportExporter(output_dir="output")
    exporter.export_json(report)
"""
