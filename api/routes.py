"""
API 路由定義 - 支援7步驟流程 (同步 TTS 版本)
"""

from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from services.test_orchestrator import TestOrchestrator
from models.test_models import TestResult, TestStatus, TestStep, STEP_DISPLAY_NAMES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["客服測試"])

test_orchestrator = None
try:
    test_orchestrator = TestOrchestrator()
except ImportError as e:
    logger.error("測試編排器初始化失敗（匯入錯誤）: %s", e)
except ValueError as e:
    logger.error("測試編排器初始化失敗（值錯誤）: %s", e)

test_results: Dict[str, TestResult] = {}


class TestRequest(BaseModel):
    """測試請求模型"""

    script: str


class TestResponse(BaseModel):
    """測試回應模型"""

    test_id: str
    status: str
    message: str


class StepDetailResponse(BaseModel):
    """步驟詳細資訊回應模型"""

    step_name: str
    step_description: str
    sub_stage: Optional[str] = None
    estimated_time_remaining: Optional[int] = None
    additional_info: Dict[str, Any] = {}


class TestStatusResponse(BaseModel):
    """測試狀態回應模型 - 增強版"""

    test_id: str
    status: str
    current_step: str
    step_progress: float
    overall_progress: float
    step_details: StepDetailResponse
    completed_steps: List[str]
    error_message: Optional[str] = None
    timestamp: str


@router.post("/test/start", response_model=TestResponse)
async def start_test(request: TestRequest, background_tasks: BackgroundTasks):
    """開始執行客服測試"""
    try:
        if not test_orchestrator:
            raise HTTPException(status_code=503, detail="測試系統尚未就緒，請稍後再試")

        if not request.script.strip():
            raise HTTPException(status_code=400, detail="測試腳本不能為空")

        result = TestResult(original_script=request.script)
        test_results[result.test_id] = result

        # --- 核心修改：將呼叫的背景函式從 run_test_async 改為 run_test ---
        background_tasks.add_task(run_test, result)

        logger.info("測試已開始，ID: %s", result.test_id)
        return TestResponse(
            test_id=result.test_id, status="running", message="測試已開始執行"
        )
    except Exception as e:
        logger.error("開始測試失敗: %s", e)
        raise HTTPException(status_code=500, detail=f"系統錯誤: {str(e)}") from e


# --- 其他路由函式 (get_test_status, get_test_result 等) 保持不變 ---


@router.get("/test/{test_id}/status", response_model=TestStatusResponse)
async def get_test_status(test_id: str) -> TestStatusResponse:
    if test_id not in test_results:
        raise HTTPException(status_code=404, detail="找不到指定的測試")
    result = test_results[test_id]
    status_data = result.get_status_response()
    # 使用 ** 解包字典來填充 Pydantic 模型
    return TestStatusResponse(**status_data)


@router.get("/test/{test_id}/result")
async def get_test_result(test_id: str) -> Dict[str, Any]:
    if test_id not in test_results:
        raise HTTPException(status_code=404, detail="找不到指定的測試")
    return test_results[test_id].to_dict()


@router.get("/test/{test_id}/report")
async def get_test_report(test_id: str) -> Dict[str, Any]:
    if test_id not in test_results:
        raise HTTPException(status_code=404, detail="找不到指定的測試")
    result = test_results[test_id]
    if result.status not in [TestStatus.COMPLETED, TestStatus.FAILED]:
        return {
            "test_id": test_id,
            "status": result.status.value,
            "current_step": result.current_step,
            "overall_progress": result.overall_progress,
            "message": (
                f"測試仍在進行中... 當前步驟: "
                f"{STEP_DISPLAY_NAMES.get(result.current_step, result.current_step)}"
            ),
        }
    if result.status == TestStatus.FAILED:
        return {
            "test_id": test_id,
            "status": result.status.value,
            "message": "測試執行失敗",
            "error": result.error_message,
            "failed_at_step": result.current_step,
            "completed_steps": result.completed_steps,
        }
    analysis = result.llm_analysis
    accuracy = result.accuracy_score
    grade = "需要改進"
    grade_color = "poor"
    if accuracy >= 90:
        grade = "優秀"
        grade_color = "excellent"
    elif accuracy >= 80:
        grade = "良好"
        grade_color = "good"
    elif accuracy >= 70:
        grade = "普通"
        grade_color = "fair"
    return {
        "test_id": test_id,
        "accuracy_score": accuracy,
        "grade": grade,
        "grade_color": grade_color,
        "summary": analysis.get("summary", ""),
        "reasoning": analysis.get("reasoning", ""),
        "key_differences": analysis.get("key_differences", []),
        "suggestions": analysis.get("suggestions", []),
        "execution_summary": {
            "total_steps": 7,
            "completed_steps": len(result.completed_steps),
            "final_step": result.current_step,
            "overall_progress": result.overall_progress,
            "test_duration": (
                (datetime.now() - result.timestamp).total_seconds()
                if result.final_report
                else 0
            ),
        },
        "step_details": {
            "preprocessing": {
                "dialogue_count": result.parsed_dialogue_count,
                "validation_info": result.script_validation_info,
            },
            "startup": {
                "apis_verified": result.apis_verified,
                "startup_info": result.startup_info,
            },
            "tts_conversion": {
                "audio_duration": result.tts_audio.duration if result.tts_audio else 0,
                "generation_info": result.tts_generation_info,
            },
            "recording": {
                "recorded_duration": (
                    result.recorded_audio.duration if result.recorded_audio else 0
                ),
                "recording_info": result.recording_info,
            },
            "storage": {
                "file_id": result.storage_file_id,
                "storage_metadata": result.storage_metadata,
            },
            "llm_analysis": {
                "stt_confidence": result.stt_confidence,
                "stt_info": result.stt_info,
                "analysis_results": analysis,
            },
            "completion": {
                "final_report": result.final_report,
                "cleanup_info": result.cleanup_info,
            },
        },
        "original_script": result.original_script,
        "transcribed_text": result.transcribed_text,
        "timestamp": result.timestamp.isoformat(),
        "audio_files": {
            "tts_audio": result.tts_audio.get_web_path() if result.tts_audio else None,
            "recorded_audio": (
                result.recorded_audio.get_web_path() if result.recorded_audio else None
            ),
        },
    }


@router.get("/test/{test_id}/steps")
async def get_test_steps(test_id: str) -> Dict[str, Any]:
    if test_id not in test_results:
        raise HTTPException(status_code=404, detail="找不到指定的測試")
    result = test_results[test_id]
    steps_status = {}
    for step_enum in TestStep:
        if step_enum == TestStep.IDLE:
            continue
        step_key = step_enum.value
        step_name = STEP_DISPLAY_NAMES.get(step_key, step_key)
        if step_key in result.completed_steps:
            status = "completed"
            progress = 100.0
        elif step_key == result.current_step:
            status = "active"
            progress = result.step_progress
        else:
            status = "pending"
            progress = 0.0
        steps_status[step_key] = {
            "step_name": step_name,
            "status": status,
            "progress": progress,
            "order": list(TestStep).index(step_enum),
        }
    return {
        "test_id": test_id,
        "current_step": result.current_step,
        "overall_progress": result.overall_progress,
        "steps": steps_status,
    }


@router.get("/system/status")
async def get_system_status() -> Dict[str, Any]:
    if not test_orchestrator:
        return {
            "status": "error",
            "message": "測試系統未就緒",
            "services": {},
            "system_info": {"available_steps": 0, "orchestrator_ready": False},
        }
    try:
        service_status = await test_orchestrator.get_service_status()
        all_services_ok = all(service_status.values())
        return {
            "status": "healthy" if all_services_ok else "partial",
            "services": service_status,
            "message": "所有服務正常" if all_services_ok else "部分服務異常",
            "system_info": {
                "available_steps": 7,
                "orchestrator_ready": True,
                "step_names": list(STEP_DISPLAY_NAMES.values()),
            },
        }
    except Exception as e:
        logger.error("系統狀態檢查失敗: %s", e)
        return {
            "status": "error",
            "message": f"狀態檢查失敗: {str(e)}",
            "services": {},
            "system_info": {"available_steps": 7, "orchestrator_ready": False},
        }


@router.get("/tests/list")
async def list_tests(limit: int = 10) -> Dict[str, Any]:
    sorted_tests = sorted(
        test_results.values(), key=lambda r: r.timestamp, reverse=True
    )
    test_list = []
    for result in sorted_tests[:limit]:
        completion_percentage = (len(result.completed_steps) / 7) * 100
        test_info = {
            "test_id": result.test_id,
            "status": result.status.value,
            "current_step": result.current_step,
            "current_step_name": STEP_DISPLAY_NAMES.get(
                result.current_step, result.current_step
            ),
            "overall_progress": result.overall_progress,
            "completion_percentage": completion_percentage,
            "accuracy_score": result.accuracy_score,
            "timestamp": result.timestamp.isoformat(),
            "script_preview": (
                result.original_script[:50] + "..."
                if len(result.original_script) > 50
                else result.original_script
            ),
            "completed_steps_count": len(result.completed_steps),
            "total_steps": 7,
        }
        test_list.append(test_info)
    return {
        "tests": test_list,
        "total": len(test_results),
        "system_info": {
            "total_steps_per_test": 7,
            "step_names": list(STEP_DISPLAY_NAMES.values()),
        },
    }


@router.delete("/test/{test_id}")
async def delete_test(test_id: str) -> Dict[str, Any]:
    if test_id not in test_results:
        raise HTTPException(status_code=404, detail="找不到指定的測試")
    result = test_results[test_id]
    if result.status == TestStatus.RUNNING:
        raise HTTPException(status_code=400, detail="無法刪除正在執行中的測試")
    del test_results[test_id]
    logger.info("測試記錄已刪除: %s", test_id)
    return {
        "message": "測試記錄已成功刪除",
        "deleted_test_id": test_id,
        "remaining_tests": len(test_results),
    }


@router.post("/tests/cleanup")
async def cleanup_old_tests(days: int = 7) -> Dict[str, Any]:
    cutoff_date = datetime.now() - timedelta(days=days)
    tests_to_delete = []
    for test_id, result in test_results.items():
        if result.status != TestStatus.RUNNING and result.timestamp < cutoff_date:
            tests_to_delete.append(test_id)
    cleanup_count = 0
    for test_id in tests_to_delete:
        del test_results[test_id]
        cleanup_count += 1
    logger.info("清理了 %d 個舊測試記錄", cleanup_count)
    return {
        "message": f"已清理 {cleanup_count} 個超過 {days} 天的舊測試記錄",
        "cleaned_count": cleanup_count,
        "remaining_tests": len(test_results),
        "cutoff_date": cutoff_date.isoformat(),
    }


# --- 核心修改：將函式名稱從 run_test_async 改為 run_test ---
async def run_test(result: TestResult):
    """在背景執行測試的異步函數"""
    try:
        logger.info("開始執行背景測試: %s", result.test_id)
        # 雖然 TestOrchestrator 內部有些步驟變為同步，但 run_full_test 本身仍為 async
        await test_orchestrator.run_full_test(result)
        logger.info("背景測試完成: %s", result.test_id)
    except ValueError as e:
        logger.error("背景測試失敗（值錯誤）(%s): %s", result.test_id, e)
        result.status = TestStatus.FAILED
        result.error_message = str(e)
    except RuntimeError as e:
        logger.error("背景測試失敗（執行錯誤）(%s): %s", result.test_id, e)
        result.status = TestStatus.FAILED
        result.error_message = str(e)
