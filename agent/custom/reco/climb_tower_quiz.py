import numpy as np
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
from maa.define import Rect

from utils import logger as logger_module
logger = logger_module.get_logger("climb_tower_quiz")


def _save_dialog_choice(image, text) -> bool:
    """对话选择时把当前截图存到 debug/对话选择存档/，供后续择优分析。

    - 命中清单词时，text 传命中的关键词（文件名便于识别）；否则传"未命中"。
    - 无论命中与否都会存一张，确保覆盖所有题目，不漏题。
    """
    try:
        from datetime import datetime
        from pathlib import Path
        import re
        from PIL import Image as PILImage
        save_dir = Path(__file__).resolve().parents[3] / "debug" / "对话选择存档"
        save_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|]', '_', str(text))
        ts = datetime.now().strftime("%Y.%m.%d.%H.%M.%S.%f")[:-3]
        PILImage.fromarray(image[:, :, :3][:, :, ::-1], mode="RGB").save(save_dir / f"{ts}_{safe}.png")
        logger.info(f"[对话选择] 已截图存档：{text}")
        return True
    except Exception as exc:
        logger.warning(f"[对话选择] 截图存档失败：{exc}")
        return False


@AgentServer.custom_recognition("quiz_recognition")
class QuizRecognition(CustomRecognition):
    ROIS = {
        2: [670, 300, 590, 230],
        3: [670, 250, 590, 325],
        4: [670, 200, 590, 450]
    }
    def analyze(
            self,
            context: Context,
            argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        answer_count = 0
        default_box = [0, 0, 0, 0]

        # 根据选项数量定位roi
        reco_result = context.run_recognition("星塔_节点_随便选择_agent", argv.image)
        if reco_result and reco_result.hit:
            answer_count = len(reco_result.filtered_results)
            default_box = reco_result.best_result.box

        # 每次进入对话选择都存一张截图（无论命中与否），确保覆盖所有题目
        _save_dialog_choice(argv.image, f"选择_选项数{answer_count}")

        if answer_count == 1:
            # 有时候因为不够金币导致只有部分选项生效
            logger.warning(f"[问题选择] 只检测到1个有效选项，选择该选项")
            return CustomRecognition.AnalyzeResult(box=default_box, detail={})

        if not answer_count or answer_count not in self.ROIS:
            logger.warning(f"[问题选择] 选项个数={answer_count} 异常，尝试兜底定位选项")
            fallback = self._fallback_box(context, argv.image, reco_result)
            if fallback:
                logger.info(f"[问题选择] 兜底选择选项 box={fallback}")
                return CustomRecognition.AnalyzeResult(box=fallback, detail={})
            logger.error(f"[问题选择] 无法定位任何选项，返回默认 box={default_box}")
            # 避免 box=None 导致点击失败：退回 default_box，无效则用对话框区域兜底
            use_box = default_box if default_box != [0, 0, 0, 0] else [600, 250, 560, 400]
            return CustomRecognition.AnalyzeResult(box=use_box, detail={})

        # 寻找最佳答案
        roi = self.ROIS[answer_count]
        result_box = self._get_best_answer(context, argv.image, roi)
        if result_box:
            return CustomRecognition.AnalyzeResult(box=result_box, detail={})

        # 寻找赌 650 金币的答案
        result_box = self._get_650_answer(context, argv.image, roi)
        if result_box:
            return CustomRecognition.AnalyzeResult(box=result_box, detail={})

        # 兜底，选择第一个选项
        logger.info(f"[问题选择] 选择第一个选项")
        # from utils.image_handler import save_image
        # save_image(argv.image, f"未知选项")
        return CustomRecognition.AnalyzeResult(box=default_box, detail={})

    @staticmethod
    def _get_best_answer(context: Context, image: np.ndarray, roi: list) -> Rect | None:
        pipeline_override = {
            "星塔_节点_进行对话选择_agent":
                {
                     "recognition": {
                         "param": {
                             "roi": roi
                         }
                    }
                }
        }
        reco_result = context.run_recognition(
            "星塔_节点_进行对话选择_agent",
            image,
            pipeline_override=pipeline_override
        )
        if reco_result and reco_result.hit:
            target_text = reco_result.best_result.text
            target_box = reco_result.best_result.box
            logger.info(f"[问题选择] 选择答案：{target_text}")
            _save_dialog_choice(image, target_text)  # 命中清单词，也存一张带词名截图
            return target_box

        return None

    @staticmethod
    def _get_650_answer(context: Context, image: np.ndarray, roi: list) -> list | None:
        pipeline_override = {
            "星塔_节点_进行对话选择_寻找650金币选项_agent":
                {
                     "recognition": {
                         "param": {
                             "roi": roi
                         }
                    }
                }
        }
        reco_result = context.run_recognition(
            "星塔_节点_进行对话选择_寻找650金币选项_agent",
            image,
            pipeline_override=pipeline_override
        )
        if reco_result and reco_result.hit:
            target_text = reco_result.best_result.text
            target_box = reco_result.best_result.box
            logger.info(f"[问题选择] 选择650金币的选项")
            logger.debug(target_text)

            fixed_box = [target_box[0], target_box[1]-55, target_box[2]-100, target_box[3]]
            return fixed_box

        return None

    @staticmethod
    def _fallback_box(context: Context, image: np.ndarray, reco_result) -> list | None:
        """选项个数识别异常时的兜底定位：依次尝试模板命中结果、对话OCR最佳结果。"""
        # 1) 取"随便选择"模板的全部命中结果中的第一个
        if reco_result and reco_result.all_results:
            return reco_result.all_results[0].box
        # 2) 用"进行对话选择"OCR 在较大的对话区域找文本，取最佳结果 box
        override = {
            "星塔_节点_进行对话选择_agent": {
                "recognition": {"param": {"roi": [560, 200, 660, 420]}}
            }
        }
        r2 = context.run_recognition("星塔_节点_进行对话选择_agent", image, override)
        if r2 and r2.hit and r2.best_result:
            return r2.best_result.box
        return None
