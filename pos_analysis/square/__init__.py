"""
pos_analysis/square — Square for Restaurants Analytics
=======================================================
Complete POS analysis pipeline for Square for Restaurants data.

Modules:
    ingest         — Load and normalize Square CSV exports
    analysis       — Core sales, payment, delivery, reservation analysis
    labor          — Labor cost and SPLH optimization
    visualizations — Professional Plotly charts for reports
    main           — Orchestration and report generation

Import example::

    from pos_analysis.square.ingest import SquareDataLoader
    from pos_analysis.square.analysis import SalesAnalyzer, LaborAnalyzer

    loader = SquareDataLoader(data_dir="/path/to/csvs")
    data = loader.load_all()

    sales = SalesAnalyzer(data).run_all()
    labor = LaborAnalyzer(data).run_all()
"""
