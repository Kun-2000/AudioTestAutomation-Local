import sys
import logging
from pathlib import Path

from services.tts_service import TTSService
from models.test_models import TestScript

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def run_tts_test():
    """
    一個簡單的函式，用來初始化並執行 TTSService。
    """
    print("\n" + "=" * 50)
    print("🚀 開始獨立測試 TTSService...")
    print("=" * 50)

    try:
        # 1. 初始化 TTSService
        #    這一步會開始載入 Coqui TTS 模型，可能會花費數分鐘。
        #    如果是第一次執行，會自動下載模型 (約 2.2 GB)。
        print("\n[步驟 1/3] 正在初始化 TTSService 並載入模型...")
        tts_service = TTSService()
        print("✅ TTSService 初始化成功！模型已載入。")

        # 2. 準備一個測試用的對話腳本
        print("\n[步驟 2/3] 準備測試腳本...")
        test_content = (
            "客戶: 你好，我想詢問產品資訊。\n"
            "客服: 很高興為您服務，請問需要什麼協助？\n"
            "客戶: 我想了解最新的優惠活動。\n"
            "客服: 當然，我們目前有多項優惠，請參考我們的官網。"
        )
        script = TestScript(content=test_content)
        print(f"📄 腳本內容:\n{test_content}")

        # 3. 執行語音生成
        print("\n[步驟 3/3] 正在執行語音生成...")
        # 注意：這一步會進行模型推理，根據您的硬體可能需要一些時間。
        audio_file_result = tts_service.generate_dialogue_audio(script)

        print("\n" + "=" * 50)
        print("🎉 測試成功！")
        print("=" * 50)
        print("🔊 音檔已成功生成！")
        print(f"📁 檔案路徑: {audio_file_result.file_path}")
        print(f"⏱️ 音檔時長: {audio_file_result.duration:.2f} 秒")
        print(f"📦 檔案大小: {audio_file_result.file_size / 1024:.2f} KB")

    except Exception as e:
        logging.error("❌ 測試過程中發生錯誤: %s", e, exc_info=True)
        print("\n" + "=" * 50)
        print("😭 測試失敗。請檢查上面的錯誤訊息。")
        print("=" * 50)


if __name__ == "__main__":
    run_tts_test()
