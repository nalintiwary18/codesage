from src.analyzer.chunking.chunker import Chunker
from src.graph.state import GraphState
from src.retrieval.selector import ChunkSelector
from src.utils.logger import get_logger
from src.analyzer.loader.file_loader import FileLoader
from src.analyzer.loader.language_detector import detect_language
from src.utils.spinner import spinner, print_success
from src.analyzer.indexing.code_index import CodeIndex


logger = get_logger(__name__)

def load_code(state:GraphState)->GraphState:
    with spinner("Loading files..."):
        loader = FileLoader(state['config'].target_path)
        state['files'] = loader.load_all_files()
        for f in state['files']:
            f.language = detect_language(f.relative_path)
        state['target'] = str(state['config'].target_path)
        print_success(f"{len(state['files'])} files loaded")
    return state


def chunked(state:GraphState)->GraphState:
    with spinner("Chunking code..."):
        state['all_chunks'] = Chunker(max_chunk_lines=50).chunk_all_files(state['files'])
        print_success(f"{len( state['all_chunks'])} chunks created")
    return state

def index(state:GraphState)->GraphState:
    with spinner("Indexing code..."):
        code_index = CodeIndex()
        code_index.add_chunks(state['all_chunks'])
        state['index'] = code_index
        state['selected'] = ChunkSelector(max_chunks=state['config'].max_chunks).select(state['index'])
        print_success(f"{len(state['selected'])} chunks selected for analysis")
    return state