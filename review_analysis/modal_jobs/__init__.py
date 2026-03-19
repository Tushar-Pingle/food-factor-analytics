"""
Modal Jobs — Serverless parallelism via Modal.com.

Modules:
- nlp_job: Batch NLP extraction on Modal (process_batch_odd, process_batch_even)
- scrape_job: Parallel scraping across platforms
- insights_job: Chef, manager, and summary generation on Modal
"""

# Note: These are designed to be imported and used with Modal's .spawn() and .remote()
# They require Modal credentials and secrets to be configured.

__all__ = [
    "nlp_job",
    "scrape_job",
    "insights_job",
]
