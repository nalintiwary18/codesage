"""
Default constants for all configuration fields.
When no value is provided via file, env, or CLI, these are the fallbacks.
Centralising defaults here prevents magic numbers scattered across the codebase.
"""

# Default LLM backend provider
DEFAULT_PROVIDER = "openai"

# Default model — low cost, fast, suitable for most codebases
DEFAULT_MODEL = "gpt-4o-mini"

# Maximum chunks per run — balances cost vs coverage
DEFAULT_MAX_CHUNKS = 50

# Where generated reports are saved
DEFAULT_OUTPUT_DIR = "./reports"

# Default report filename
DEFAULT_OUTPUT_FILENAME = "report.md"

# Caching is on by default — unchanged chunks are skipped to save tokens
DEFAULT_CACHE_ENABLED = True

# Issues with confidence below this threshold are excluded from the report
DEFAULT_MIN_CONFIDENCE = 0.5

# Logging verbosity — INFO is sufficient for production use
DEFAULT_LOG_LEVEL = "INFO"

# Filename for the optional per-project config file
CONFIG_FILE_NAME = ".codesage.yml"

# Subdirectory under project root used for caching analysis results
CACHE_DIR_NAME = ".codesage_cache"

# Extension → language tag mapping used by the language detector
SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".lua": "lua",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".sql": "sql",
}

# Extensions that identify binary files — these are always skipped
BINARY_EXTENSIONS: set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".wav", ".avi",
    ".zip", ".tar", ".gz", ".rar",
    ".exe", ".dll", ".so", ".dylib",
    ".pdf", ".doc", ".docx", ".xls",
    ".pyc", ".pyo", ".class", ".o",
    ".woff", ".woff2", ".ttf", ".eot",
    ".db", ".sqlite", ".sqlite3",
}

# Directory names that are always excluded from file loading
DEFAULT_IGNORE_DIRS: set[str] = {
    "__pycache__", ".git", ".svn", ".hg",
    "node_modules", ".venv", "venv",
    ".idea", ".vscode", ".codesage_cache",
    "dist", "build", ".egg-info",
}

# Files larger than this are skipped — prevents loading huge generated files
MAX_FILE_SIZE_BYTES = 5_000_000  # 5 MB

# Chunks longer than this are split at natural boundaries
MAX_CHUNK_LINES = 200

# Model options shown in the interactive wizard per provider
PROVIDER_MODELS: dict[str, list[str]] = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"],
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
    "groq": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    "ollama": ["llama3.1", "codellama", "mistral", "deepseek-coder"],
}

# Language choices shown in the interactive wizard
SUPPORTED_LANGUAGES: list[str] = [
    "JavaScript / TypeScript",
    "Python",
    "Go",
    "Rust",
    "Java",
    "Other",
]
