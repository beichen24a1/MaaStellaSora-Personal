"""灾变防线：上半结束后的走位进传送门（个人版新增）。

灾变防线的战斗分上下半场，上半打完后要手动操作角色走到场地中央的传送门才能进下半。
自动化的做法是「试探式」：不必精确判断上半何时结束，隔一段时间就尝试一次走位，
按用户实测有效的按键组合操作，任一环节进入加载（黑屏）即视为进门成功。

按键：先按住 W+A 若干秒走向左上角，再按住 S+D 走向中央传送门；
按住期间每秒截一次屏，检测到黑屏（进入加载）就立刻松键。

本模块同时提供 catastrophe_defense_reset，在任务入口重置状态，
保证同一进程内反复跑任务时走位逻辑不会因为上次的标记而被跳过。
"""

from __future__ import annotations

import time

import numpy as np
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from utils import logger as logger_module

logger = logger_module.get_logger("catastrophe_defense")

## Win32 虚拟键码
KEY_W = 0x57
KEY_A = 0x41
KEY_S = 0x53
KEY_D = 0x44

## 整屏平均亮度低于该值即认为进了加载（黑屏）
BLACK_MEAN_THRESHOLD = 25.0

## 走位参数（秒）
WALK_LEFT_SECONDS = 10.0
WALK_PORTAL_SECONDS = 4.0

## 本次任务是否已经走位过（由 reset 动作清零）
_moved = False


def _screen_mean(context: Context) -> float | None:
    """当前画面平均亮度；取不到图返回 None。"""

    image = context.tasker.controller.post_screencap().wait().get()
    if image is None:
        return None
    return float(np.asarray(image).mean())


def _hold(
    context: Context, keys: list[int], seconds: float, *, watch_black: bool = False
) -> bool:
    """按住一组键 seconds 秒；watch_black=True 时每秒检测一次是否已进加载。

    Returns:
        bool: 按住期间是否检测到黑屏（= 进了传送门 / 加载）。
    """

    controller = context.tasker.controller
    for key in keys:
        controller.post_key_down(key).wait()

    entered = False
    try:
        deadline = time.time() + seconds
        while time.time() < deadline:
            time.sleep(1.0)
            if not watch_black:
                continue
            mean = _screen_mean(context)
            if mean is not None and mean < BLACK_MEAN_THRESHOLD:
                entered = True
                break
    finally:
        for key in reversed(keys):
            controller.post_key_up(key).wait()
    return entered


@AgentServer.custom_action("catastrophe_defense_reset")
class CatastropheDefenseReset(CustomAction):
    """任务开始时清掉上一次运行留下的走位标记。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        global _moved
        _moved = False
        logger.debug("灾变防线：已重置走位标记")
        return True


@AgentServer.custom_action("catastrophe_defense_move")
class CatastropheDefenseMove(CustomAction):
    """试探式走位进传送门；同一轮任务只真正执行一次。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        global _moved

        if _moved:
            ## 已经走位过：直接去看有没有挑战成功，不要再阻塞主循环
            context.override_next(argv.node_name, ["灾变防线_挑战成功"])
            return True

        node_data = context.get_node_data(argv.node_name) or {}
        attach = node_data.get("attach", {}) or {}
        first_wait = float(attach.get("first_wait", 150))
        retry_wait = float(attach.get("retry_wait", 20))
        attempts = int(attach.get("attempts", 8))

        logger.info(
            f"灾变防线：等待 {first_wait:.0f} 秒后开始试探走位（上半约需 3~4 分钟）"
        )
        ## 分段等待并打心跳日志 —— 一次性 sleep 会让外界以为任务卡死了
        waited = 0.0
        while waited < first_wait:
            step = min(10.0, first_wait - waited)
            time.sleep(step)
            waited += step
            logger.info(f"灾变防线：等待中 {waited:.0f}/{first_wait:.0f} 秒")

        for attempt in range(1, attempts + 1):
            logger.info(f"灾变防线：第 {attempt}/{attempts} 次试探走位")
            remaining = attempts - attempt
            logger.debug(f"灾变防线：本轮走位后剩余 {remaining} 次机会")
            if _hold(context, [KEY_W, KEY_A], WALK_LEFT_SECONDS, watch_black=True):
                logger.info("灾变防线：按 W+A 途中已进入传送门")
                _moved = True
                context.override_next(argv.node_name, ["灾变防线_战斗循环"])
                return True
            if _hold(context, [KEY_S, KEY_D], WALK_PORTAL_SECONDS, watch_black=True):
                logger.info("灾变防线：按 S+D 后已进入传送门")
                _moved = True
                context.override_next(argv.node_name, ["灾变防线_战斗循环"])
                return True
            if attempt < attempts:
                time.sleep(retry_wait)

        logger.warning("灾变防线：试探走位达到上限仍未进门，交回主循环")
        _moved = True
        context.override_next(argv.node_name, ["灾变防线_战斗循环"])
        return True
