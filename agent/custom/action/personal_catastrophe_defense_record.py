"""灾变防线：从「纪录管理」页里挑出可选的那张记录卡（个人版新增）。

【为什么不能直接点模板匹配的结果】
上游的 选择纪录_选择首个纪录 用 choose_record/record_position.png 匹配卡片上的小
徽标，再 order_by: Vertical 取最上面那张。可那个徽标**每张记录卡都有** —— 实测
一屏 8 张卡全部命中（分数 0.88~0.99，阈值 0.7 全部通过），而这一页里绝大多数卡
是**灰色不可选**的（本期已经用过的记录），点上去毫无反应，于是流程就卡死在
纪录管理页，最后 Node.NextList.Failed 把整个任务判失败。

【怎么区分可选卡】
灰卡是**整张被蒙了一层灰**：亮度与饱和度都明显低。实测（用户截图，客户区坐标）：
    可选（高亮）那张：整卡亮度 192、饱和度 0.227
    其余 7 张        ：亮度最高 141、饱和度最高 0.141
所以判据取「亮度 + 100×饱和度」，挑分数最高的那张点。采样区域是相对徽标位置的
偏移（不写死屏幕坐标），换分辨率/换页也能跟着徽标走。

模板匹配那一层负责「找出所有卡片」（把 <0.7 的噪音挡掉），本动作负责在候选里
挑最亮最彩的那张 —— 两者分工，互不越界。
"""

from __future__ import annotations

import numpy as np
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from utils import logger as logger_module

logger = logger_module.get_logger("catastrophe_defense")

## 记录卡区域相对「◈ 旅人」徽标的偏移（x, y, w, h）
CARD_OFFSET = (-20, -71, 230, 250)

## 点击位置相对徽标的偏移（取卡片中心）
CLICK_OFFSET = (95, 55)


def _grab(context: Context):
    """截一帧；失败返回 None。"""

    try:
        return context.tasker.controller.post_screencap().wait().get()
    except Exception:  # noqa: BLE001 - 任务停止时框架会拒绝截图
        return None


def _card_score(arr, icon_x: int, icon_y: int) -> float:
    """量一张记录卡「有多亮多彩」；灰卡被蒙灰，分数明显低。"""

    dx, dy, w, h = CARD_OFFSET
    x0 = max(0, icon_x + dx)
    y0 = max(0, icon_y + dy)
    patch = arr[y0:y0 + h, x0:x0 + w]
    if patch.size == 0:
        return -1.0
    p = patch.astype(np.float32)
    mx = p.max(axis=2)
    mn = p.min(axis=2)
    sat = float(((mx - mn) / np.maximum(mx, 1.0)).mean())
    return float(p.mean()) + 100.0 * sat


@AgentServer.custom_action("catastrophe_defense_pick_record")
class CatastropheDefensePickRecord(CustomAction):
    """在「纪录管理」页挑出可选（高亮）的那张记录卡并点击。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        if context.tasker.stopping:
            return False

        image = _grab(context)
        if image is None:
            logger.error("灾变防线：纪录管理页截图失败")
            return False

        ## 复用当前节点的模板识别，拿到页面上所有记录卡（每张卡一个小徽标）
        detail = context.run_recognition(argv.node_name, image)
        if detail is None or not detail.hit:
            logger.error("灾变防线：纪录管理页没有识别到任何记录卡")
            return False

        candidates = list(detail.filtered_results or detail.all_results or [])
        if not candidates:
            logger.error("灾变防线：记录卡候选为空")
            return False

        arr = np.asarray(image)
        scored = []
        for r in candidates:
            x, y, _w, _h = r.box
            scored.append((_card_score(arr, x, y), x, y, r.score))
        scored.sort(key=lambda t: -t[0])

        best_score, best_x, best_y, match_score = scored[0]
        logger.info(
            "灾变防线：纪录管理页 %d 张记录卡，选中分数最高的一张（%.1f，模板分 %.3f，位置 %d,%d）",
            len(scored), best_score, match_score, best_x, best_y,
        )
        logger.debug("灾变防线：各卡分数 %s", [round(s[0], 1) for s in scored])

        if best_score < 0:
            logger.error("灾变防线：记录卡采样失败")
            return False

        click_x = best_x + CLICK_OFFSET[0]
        click_y = best_y + CLICK_OFFSET[1]
        if context.tasker.stopping:
            return False
        if not context.tasker.controller.post_click(click_x, click_y).wait().succeeded:
            logger.error("灾变防线：点击记录卡失败")
            return False
        logger.info("灾变防线：已选择记录卡（点击 %d,%d）", click_x, click_y)
        return True
