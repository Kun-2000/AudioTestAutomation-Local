"""
TTS 服務模組 - 修改為使用 Coqui TTS 的 Python API 直接整合
"""

from pathlib import Path
import logging
import uuid
import os
import torch

from TTS.api import TTS
from config.settings import settings
from models.test_models import TestScript, SpeakerRole, AudioFile
from utils.audio_utils import (
    combine_audio_segments,
    create_silence,
    get_audio_duration,
)

logger = logging.getLogger(__name__)


class TTSService:
    """Coqui TTS 地端服務 (直接整合)"""

    def __init__(self):
        """初始化 Coqui TTS 地端服務並載入模型"""
        try:
            # 偵測是否有可用的 GPU
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("TTS 服務將使用裝置: %s", self.device)

            # 載入 XTTS v2 模型
            # 注意：這一步會在主專案啟動時執行，可能會花費一些時間
            logger.info("正在載入 XTTS v2 模型，請稍候...")
            self.tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(
                self.device
            )
            logger.info("XTTS v2 模型載入成功。")

            # 定義不同角色的參考音檔路徑
            self.voice_mapping = {
                SpeakerRole.CUSTOMER: settings.COQUI_TTS_SPEAKER_CUSTOMER_WAV,
                SpeakerRole.AGENT: settings.COQUI_TTS_SPEAKER_AGENT_WAV,
            }

        except Exception as e:
            logger.error("Coqui TTS 服務初始化或模型載入失敗: %s", e)
            raise

    # 注意：由於模型推理是同步操作，我們將 generate_dialogue_audio 改為同步函式
    # FastAPI 的背景任務可以很好地處理同步函式，不會阻塞主線程
    def generate_dialogue_audio(self, test_script: TestScript) -> AudioFile:
        """從測試腳本生成對話音檔 (同步版本)"""
        dialogue_lines = test_script.parse_content()
        if not dialogue_lines:
            raise ValueError("腳本中沒有可識別的對話內容")

        logger.info(
            "開始生成對話音檔 (Coqui TTS Direct API)，共 %d 行對話", len(dialogue_lines)
        )

        temp_audio_files = []
        try:
            for i, line in enumerate(dialogue_lines):
                # 為每一段語音生成一個臨時檔案
                temp_path = str(
                    settings.TEMP_PATH / f"segment_{uuid.uuid4().hex[:8]}.wav"
                )
                self._synthesize_speech(line.text, line.speaker, temp_path)
                temp_audio_files.append(temp_path)

                # 在對話之間插入靜音
                if i < len(dialogue_lines) - 1:
                    silence_path = str(
                        settings.TEMP_PATH / f"silence_{uuid.uuid4().hex[:8]}.wav"
                    )
                    silence_bytes = create_silence(line.pause_after)
                    with open(silence_path, "wb") as f:
                        f.write(silence_bytes)
                    temp_audio_files.append(silence_path)

            # 讀取所有片段的 bytes
            audio_segments_bytes = [Path(p).read_bytes() for p in temp_audio_files]

            # 合併所有音檔片段
            combined_audio = combine_audio_segments(
                audio_segments_bytes, output_format="wav"
            )

            # 儲存最終的合併檔案
            filename = f"dialogue_coqui_{uuid.uuid4().hex[:8]}.wav"
            final_file_path = settings.AUDIO_PATH / filename
            with open(final_file_path, "wb") as f:
                f.write(combined_audio)

            duration = get_audio_duration(final_file_path)
            file_size = final_file_path.stat().st_size

            audio_file = AudioFile(
                file_path=str(final_file_path),
                duration=duration,
                file_size=file_size,
                format="wav",
            )
            logger.info(
                "對話音檔生成成功 (Coqui TTS Direct API): %s, 時長: %.1f秒",
                filename,
                duration,
            )
            return audio_file
        finally:
            # 清理所有臨時檔案
            for path in temp_audio_files:
                try:
                    os.remove(path)
                except OSError as e:
                    logger.warning("無法刪除臨時檔案 %s: %s", path, e)

    def _synthesize_speech(self, text: str, speaker: SpeakerRole, file_path: str):
        """使用 Coqui TTS API 將單段文字合成語音並存檔"""
        try:
            speaker_wav_path = self.voice_mapping[speaker]

            self.tts_model.tts_to_file(
                text=text.strip(),
                speaker_wav=speaker_wav_path,
                language="zh-cn",  # 指定中文
                file_path=file_path,
            )
        except Exception as e:
            logger.error("Coqui TTS 底層合成失敗: %s", e)
            raise

    def test_connection(self) -> bool:
        """測試 Coqui TTS 連接 (同步版本)"""
        try:
            if not os.path.exists(settings.COQUI_TTS_SPEAKER_CUSTOMER_WAV):
                logger.error(
                    "客戶參考音檔不存在: %s", settings.COQUI_TTS_SPEAKER_CUSTOMER_WAV
                )
                return False

            temp_path = str(
                settings.TEMP_PATH / f"connection_test_{uuid.uuid4().hex[:8]}.wav"
            )
            self._synthesize_speech("測試", SpeakerRole.CUSTOMER, temp_path)

            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                os.remove(temp_path)
                logger.info("Coqui TTS 連接測試成功")
                return True
            else:
                logger.error("Coqui TTS 連接測試失敗，未生成有效的音檔。")
                return False
        except Exception as e:
            logger.error("Coqui TTS 連接測試失敗: %s", e)
            return False
