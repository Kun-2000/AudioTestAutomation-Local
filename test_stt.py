import sys
import logging
import asyncio
from pathlib import Path
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# flake8: noqa: E402
from services.stt_service import STTService

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_stt_test():
    """
    一個簡單的函式，用來初始化並執行 STTService。
    它會讀取一個由 test_tts.py 生成並保留下來的音檔。
    """
    print("\n" + "=" * 50)
    print("🚀 開始獨立測試 STTService (使用已生成的音檔)...")
    print("=" * 50)

    # --- 步驟 1: 設定並檢查音檔路徑 ---
    audio_file_to_test = "storage/audio/dialogue_coqui_f7a05567.wav"

    test_audio_path = project_root / audio_file_to_test

    print(f"\n[步驟 1/3] 正在檢查測試音檔: {test_audio_path}...")
    if not test_audio_path.exists():
        print(f"\n😭 錯誤：找不到測試音檔 '{test_audio_path}'。")
        print("   請先執行 'python test_tts.py'，然後將其輸出的檔案路徑貼到本腳本中。")
        return
    print("✅ 測試音檔存在！")

    try:
        # --- 步驟 2: 初始化 STTService ---
        print("\n[步驟 2/3] 正在初始化 STTService 並載入模型...")
        stt_service = STTService()
        print("✅ STTService 初始化成功！")

        # --- 步驟 3: 執行語音轉錄 ---
        print(f"\n[步驟 3/3] 正在轉錄音檔: {test_audio_path.name}...")
        transcript, confidence = await stt_service.transcribe_audio(
            str(test_audio_path)
        )

        print("\n" + "=" * 50)
        print("🎉 測試成功！")
        print("=" * 50)
        print("🎤 語音轉錄已完成！")
        print(f"📝 轉錄結果: {transcript}")
        print(f"📊 可信度 (固定值): {confidence:.2f}")

    except Exception as e:
        logging.error("❌ 測試過程中發生錯誤: %s", e, exc_info=True)
        print("\n" + "=" * 50)
        print("😭 測試失敗。請檢查上面的錯誤訊息。")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_stt_test())
