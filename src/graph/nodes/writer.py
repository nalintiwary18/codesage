from pathlib import Path
from src.graph.state import GraphState
from src.agents.tasks.writer_agent import run_writer_agent
from src.utils.spinner import spinner, print_success, print_info
from src.core.mapping import ChunkMapper
from src.validation.structural import StructuralValidator
from src.validation.semantic import validate_all_semantic
from src.validation.scoring import apply_quality_scores, filter_by_quality
from src.issues.scorer import score_all_issues
from src.issues.scoring import filter_by_confidence
from src.report.markdown import MarkdownReportGenerator
from src.storage.filesystem import ReportStorage



def polish(state:GraphState)->GraphState:
    with spinner("Polishing findings..."):
        state['polished'] = run_writer_agent( state["llm"], state["reviewed"] )
        print_success(f"{len( state['polished'])} issues after polishing")
    return state


def validate(state: GraphState) -> GraphState:
    with spinner("Validating issues..."):
        mapper = ChunkMapper(state["all_chunks"])
        state['validated'] = StructuralValidator(mapper, state['target']).validate_all(state['polished'])
        state['validated'] = validate_all_semantic(state['validated'])
        state['validated'] = score_all_issues(state['validated'])
        state['validated'] = apply_quality_scores(state['validated'])
        state['validated'] = filter_by_quality(state['validated'])
        state['validated'] = filter_by_confidence(state['validated'], state["config"].min_confidence)
    print_success(f"{len(state['validated'])} issues after validation")
    if not state['validated']:
        print_info("All issues were filtered out during validation — no real issues found.")
    return state


def report(state:GraphState)->GraphState:
    with spinner("Generating report..."):

        project_name = Path(state['target']).resolve().name
        report = MarkdownReportGenerator(project_name=project_name).generate(state['validated'])
        state['saved_path'] = ReportStorage(state["config"].output_dir).save_report(
            report, filename=state["config"].output_filename
        )
    return state