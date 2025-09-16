"""
客服測試系統配置模組
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# 基礎路徑
_BASE_DIR = Path(__file__).parent.parent
STORAGE_DIR = _BASE_DIR / "storage"

# 建立必要目錄
for folder in ["audio", "reports", "temp"]:
    (STORAGE_DIR / folder).mkdir(parents=True, exist_ok=True)


class Settings:
    """系統設定類別"""

    BASE_DIR: Path = _BASE_DIR

    # 地端 LLM 設定 (Ollama)
    LLM_API_BASE_URL: str = os.getenv("LLM_API_BASE_URL", "http://localhost:11434/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "ollama")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.2:latest")

    # 地端 STT 設定 (faster-whisper)
    STT_MODEL_SIZE: str = os.getenv("STT_MODEL_SIZE", "small")
    STT_COMPUTE_TYPE: str = os.getenv("STT_COMPUTE_TYPE", "float32")
    STT_PROMPT: str = os.getenv("STT_PROMPT", "繁體中文")

    # Coqui TTS 設定 (直接整合)
    _customer_wav_path = os.getenv("COQUI_TTS_SPEAKER_CUSTOMER_WAV", "")
    COQUI_TTS_SPEAKER_CUSTOMER_WAV: str = (
        str(BASE_DIR / _customer_wav_path) if _customer_wav_path else ""
    )

    _agent_wav_path = os.getenv("COQUI_TTS_SPEAKER_AGENT_WAV", "")
    COQUI_TTS_SPEAKER_AGENT_WAV: str = (
        str(BASE_DIR / _agent_wav_path) if _agent_wav_path else ""
    )

    # 系統設定
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    MAX_AUDIO_DURATION: int = int(os.getenv("MAX_AUDIO_DURATION", "300"))

    # 路徑設定
    STORAGE_PATH: Path = STORAGE_DIR
    AUDIO_PATH: Path = STORAGE_DIR / "audio"
    REPORTS_PATH: Path = STORAGE_DIR / "reports"
    TEMP_PATH: Path = STORAGE_DIR / "temp"

    @classmethod
    def validate_config(cls) -> bool:
        """驗證必要配置"""

        return True


settings = Settings()
