import sys
import logging
import asyncio
import json
from pathlib import Path

from services.llm_service import LLMService

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_llm_test():
    """
    一個簡單的函式，用來初始化並執行 LLMService。
    """
    print("\n" + "=" * 50)
    print("🚀 開始獨立測試 LLMService (本地 Ollama)...")
    print("=" * 50)

    try:
        # --- 步驟 1: 準備測試用的文字 ---
        print("\n[步驟 1/3] 準備測試腳本與轉錄文字...")
        original_script = (
            "客戶: 你好，我想查詢我的訂單狀態。\n客服: 好的，請問您的訂單編號是多少？"
        )
        transcribed_text = (
            "客戶: 你好我想查詢我的訂單狀態\n客服: 好的請問您的訂單編號是多少"
        )

        print("\n📜 原始腳本:")
        print(original_script)
        print("\n📝 模擬轉錄文字:")
        print(transcribed_text)

        # --- 步驟 2: 初始化 LLMService ---
        print("\n[步驟 2/3] 正在初始化 LLMService...")
        print("（請確保您的本地 Ollama 服務正在運行）")
        llm_service = LLMService()
        print(f"✅ LLMService 初始化成功！模型: {llm_service.model}")

        # --- 步驟 3: 執行對話分析 ---
        print("\n[步驟 3/3] 正在執行對話分析...")
        analysis_result = await llm_service.analyze_conversation(
            original_script, transcribed_text
        )

        print("\n" + "=" * 50)
        print("🎉 測試成功！")
        print("=" * 50)
        print("🤖 LLM 分析已完成！")

        # 將結果格式化為易於閱讀的 JSON 格式
        pretty_json = json.dumps(analysis_result, indent=2, ensure_ascii=False)
        print(pretty_json)

    except Exception as e:
        logging.error("❌ 測試過程中發生錯誤: %s", e, exc_info=True)
        print("\n" + "=" * 50)
        print("😭 測試失敗。請檢查上面的錯誤訊息。")
        print("   可能的原因：")
        print("   1. 本地的 Ollama 服務未啟動。")
        print("   2. .env 檔案中的 LLM_API_BASE_URL 或 LLM_MODEL 設定不正確。")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_llm_test())
