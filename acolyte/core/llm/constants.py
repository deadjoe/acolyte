"""
LLM常量定义

定义LLM相关的常量，如提供商名称、模型名称等。
"""

# 提供商名称
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_OPENAI = "openai"
PROVIDER_GEMINI = "gemini"
PROVIDER_DEEPSEEK = "deepseek"
PROVIDER_OLLAMA = "ollama"

# 提供商URL特征
PROVIDER_URL_PATTERNS = {
    PROVIDER_ANTHROPIC: ["anthropic.com", "claude-api"],
    PROVIDER_OPENAI: ["openai.com", "azure-openai"],
    PROVIDER_GEMINI: ["googleapis.com", "generativelanguage", "gemini"],
    PROVIDER_DEEPSEEK: ["deepseek.ai", "deepseek-api"],
    PROVIDER_OLLAMA: ["ollama.ai", "ollama.com", "ollama"],
}

# 模型名称特征
MODEL_NAME_PATTERNS = {
    PROVIDER_ANTHROPIC: ["claude", "anthropic"],
    PROVIDER_OPENAI: ["gpt", "davinci", "openai"],
    PROVIDER_GEMINI: ["gemini", "palm", "google"],
    PROVIDER_DEEPSEEK: ["deepseek"],
    PROVIDER_OLLAMA: ["llama", "mistral", "mixtral", "vicuna", "phi", "yi"],
}

# 默认API URLs
DEFAULT_API_URLS = {
    PROVIDER_ANTHROPIC: "https://api.anthropic.com/v1",
    PROVIDER_OPENAI: "https://api.openai.com/v1",
    PROVIDER_GEMINI: "https://generativelanguage.googleapis.com/v1beta",
    PROVIDER_DEEPSEEK: "https://api.deepseek.ai/v1",
    PROVIDER_OLLAMA: "http://localhost:11434/api",
}

# 最大重试次数
MAX_RETRIES = 3

# 重试延迟（秒）
RETRY_DELAY = 1.0

# 超时设置（秒）
DEFAULT_TIMEOUT = 60.0

# 需要重试的HTTP状态码
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]

# 模型重试状态码
MODEL_SPECIFIC_RETRY_CODES = {
    PROVIDER_ANTHROPIC: [408, 425, 429, 500, 502, 503, 504],
    PROVIDER_OPENAI: [408, 429, 500, 502, 503, 504],
    PROVIDER_GEMINI: [408, 429, 500, 502, 503, 504],
    PROVIDER_DEEPSEEK: [408, 429, 500, 502, 503, 504],
    PROVIDER_OLLAMA: [408, 429, 500, 502, 503, 504],
}
