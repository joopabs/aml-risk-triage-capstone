"""Optional batch-triage UI (specs/002-batch-triage-ui).

A Streamlit front end that calls the local scoring service (FastAPI, the Step 8 deployment of
record) to score and rank a batch of synthetic PaySim-style transactions for human review. This
package is optional: no core module may import it, it has its own pinned requirements
(`requirements-ui.txt`), and removing it leaves the pipeline, the service, and the report intact.
"""
