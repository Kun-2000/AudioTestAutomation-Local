"""
STT 服務模組 - 使用 faster-whisper (地端版本)
"""

import logging
from pathlib import Path
from typing import Tuple
import torch
from faster_whisper import WhisperModel

from config.settings import settings

logger = logging.getLogger(__name__)


class STTService:
    """faster-whisper 地端 STT 服務"""

    def __init__(self):
        """初始化 STT 服務"""
        try:
            # 根據硬體自動選擇裝置 (GPU or CPU)
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

            # 從設定檔讀取模型大小與計算類型
            model_size = settings.STT_MODEL_SIZE
            compute_type = settings.STT_COMPUTE_TYPE

            # 載入 faster-whisper 模型
            self.model = WhisperModel(
                model_size,
                device=self.device,
                compute_type=compute_type,
            )

            self.prompt = settings.STT_PROMPT
            logger.info(
                "STT 服務 (地端 faster-whisper) 初始化成功, 模型: %s, 裝置: %s, 計算類型: %s",
                model_size,
                self.device,
                compute_type,
            )
        except Exception as e:
            logger.error("STT 服務初始化失敗: %s", e)
            raise

    async def transcribe_audio(self, audio_file_path: str) -> Tuple[str, float]:
        """使用 faster-whisper 轉錄音檔，並提供高頻率的進度回饋"""
        try:
            audio_path = Path(audio_file_path)
            if not audio_path.exists():
                raise FileNotFoundError(f"音檔不存在: {audio_file_path}")

            logger.info("開始地端轉錄音檔: %s", audio_path.name)

            # 停用 VAD 濾波器以確保完整轉錄
            segments, _ = self.model.transcribe(
                str(audio_path),
                language="zh",
                initial_prompt=self.prompt,
                vad_filter=False,
            )

            all_text = []
            print("\n轉錄進度 (處理中，請耐心等候...):")

            segment_count = 0
            for segment in segments:
                segment_count += 1
                print(
                    f"  已處理完第 {segment_count} 個音訊片段 -> 內容: '{segment.text.strip()}'"
                )
                all_text.append(segment.text)

            transcript = "".join(all_text).strip()
            print("...轉錄完成！")

            if not transcript:
                logger.warning("轉錄結果為空，檔案可能不包含有效語音")
                transcript = ""

            confidence = 0.95

            logger.info(
                "轉錄成功: %s%s",
                transcript[:50],
                "..." if len(transcript) > 50 else "",
            )
            return transcript, confidence
        except Exception as e:
            logger.error("STT 服務錯誤: %s", e)
            raise RuntimeError(f"語音轉錄失敗: {e}") from e

    async def test_connection(self) -> bool:
        """測試服務是否已成功初始化"""
        return hasattr(self, "model") and self.model is not None
