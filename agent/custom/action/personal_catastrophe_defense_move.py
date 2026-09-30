"""灾变防线：上半结束后的走位进传送门（个人版新增）。

灾变防线的战斗分上下半场，上半打完后要手动操作角色走到场地中央的传送门才能进下半。
自动化做法是「试探式」：不必精确判断上半何时结束，等够时间就试一次走位，
按用户实测有效的按键组合操作，任一环节进入加载（黑屏）即视为进门成功。

按键：先按住 W+A 约 10 秒走向左上角，再按住 S+D 走向中央传送门。

【为什么调用必须快进快出（踩过的坑）】
CustomAction.run() 执行期间，整条 pipeline 都在等它返回 —— 它跑多久，战斗循环就
卡多久。上半场全程都在弹「命运卡片」，如果这个动作一进来就闷头等 150 秒，卡片
就完全没人点了。所以：
  - 等上半场结束的阶段（PHASE_WAIT / PHASE_RETRY）：立刻返回，把控制权交回战斗
    循环，让「命运卡片_拿走」每轮都能被识别到；
  - 真正走位的阶段（PHASE_LEFT / PHASE_PORTAL）：才连续按住方向键，此时已经在
    半场交替的间隙，本来也没有卡片要点。
每一步等待都检查 context.tasker.stopping，用户点停止能立刻响应。

【等待为什么不用 time.sleep】
CustomAction.run() 跑在 agent 的消息处理线程上，长时间 sleep 会让整个 agent
停止响应（客户端截图不再更新、任务停不掉）。所以等待全部用框架截图驱动
（反复 post_screencap().wait()），既不阻塞 agent，每轮还顺带检查一次是否黑屏。
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

## 走位阶段
PHASE_WAIT = "wait"  ## 等上半场打完（每轮秒回，让战斗循环照常识别命运卡片）
PHASE_LEFT = "left"  ## 按住 W+A 走向左上角
PHASE_PORTAL = "portal"  ## 按住 S+D 走向中央传送门
PHASE_RETRY = "retry"  ## 一轮没进门，歇一会儿再来（每轮秒回）
PHASE_DONE = "done"  ## 已进门 / 已达上限，不再走位

## 走位状态（由 reset 动作清零）
_state: dict = {}


def _reset_state() -> None:
    _state.clear()
    _state.update(started_at=None, phase=PHASE_WAIT, attempt=0, retry_until=0.0, entered=False)


_reset_state()


def _grab(context: Context):
    """截一帧；失败返回 None。"""

    try:
        return context.tasker.controller.post_screencap().wait().get()
    except Exception:  # noqa: BLE001 - 任务停止时框架会拒绝截图
        return None


def _is_black(image) -> bool:
    """整屏平均亮度过低即认为在加载（黑屏）；隔点采样，够用且快。"""

    if image is None or getattr(image, "size", 0) == 0:
        return False
    return float(np.asarray(image)[::8, ::8].mean()) < BLACK_MEAN_THRESHOLD


def _hold(context: Context, keys: tuple[int, ...], seconds: float) -> str:
    """按住一组键 seconds 秒（用截图驱动等待），结束一定松开。

    Returns:
        str: "entered" 检测到黑屏；"stopped" 用户点了停止；"timeout" 按满时间没进门。
    """

    controller = context.tasker.controller
    for key in keys:
        controller.post_key_down(key).wait()

    outcome = "timeout"
    try:
        deadline = time.time() + seconds
        while time.time() < deadline:
            if context.tasker.stopping:
                outcome = "stopped"
                break
            if _is_black(_grab(context)):
                outcome = "entered"
                break
    finally:
        for key in reversed(keys):
            try:
                controller.post_key_up(key).wait()
            except Exception:  # noqa: BLE001 - 任务停止时按键任务可能已失效
                pass
    return outcome


@AgentServer.custom_action("catastrophe_defense_reset")
class CatastropheDefenseReset(CustomAction):
    """任务开始时清掉上一次运行留下的走位状态。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        _reset_state()
        logger.debug("灾变防线：已重置走位状态")
        return True


@AgentServer.custom_action("catastrophe_defense_move")
class CatastropheDefenseMove(CustomAction):
    """试探式走位进传送门：等待阶段秒回，只在走位阶段连续按键。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        if context.tasker.stopping or _state.get("entered"):
            return True

        node_data = context.get_node_data(argv.node_name) or {}
        attach = node_data.get("attach", {}) or {}
        first_wait = float(attach.get("first_wait", 210))
        left_seconds = float(attach.get("left_seconds", 12))
        portal_seconds = float(attach.get("portal_seconds", 5))
        attempts = int(attach.get("attempts", 8))
        retry_wait = float(attach.get("retry_wait", 20))

        now = time.time()

        ## 首次被调用：只记时间，立刻让战斗循环回去识别命运卡片
        if _state.get("started_at") is None:
            _state["started_at"] = now
            _state["phase"] = PHASE_WAIT
            logger.info(f"灾变防线：进入战斗循环，{first_wait:.0f} 秒后开始试探走位")
            return True

        phase = _state.get("phase", PHASE_WAIT)

        ## 等上半场打完：本动作秒回，战斗循环每轮都会重新识别命运卡片
        if phase == PHASE_WAIT:
            if now - _state["started_at"] >= first_wait:
                _state["phase"] = PHASE_LEFT
                _state["attempt"] = 1
                logger.info(f"灾变防线：开始第 1/{attempts} 次试探走位")
            return True

        ## 一轮没进门：歇 retry_wait 秒，这期间同样秒回，卡片照常识别
        if phase == PHASE_RETRY:
            if now >= _state.get("retry_until", 0.0):
                _state["phase"] = PHASE_LEFT
                logger.info(f"灾变防线：开始第 {_state.get('attempt', 1)}/{attempts} 次试探走位")
            return True

        if phase == PHASE_LEFT:
            keys, seconds = (KEY_W, KEY_A), left_seconds
        elif phase == PHASE_PORTAL:
            keys, seconds = (KEY_S, KEY_D), portal_seconds
        else:
            return True

        ## 连续按住方向键；期间每轮截图检查是否进了加载
        outcome = _hold(context, keys, seconds)

        if outcome == "stopped":
            return True

        if outcome == "entered":
            _state["entered"] = True
            _state["phase"] = PHASE_DONE
            logger.info("灾变防线：检测到加载黑屏，已进入传送门")
            return True

        if phase == PHASE_LEFT:
            _state["phase"] = PHASE_PORTAL
            logger.info("灾变防线：左上角已走到，改按 S+D 走向中央传送门")
            return True

        ## PHASE_PORTAL 按满仍未进门
        attempt = _state.get("attempt", 1)
        if attempt >= attempts:
            _state["phase"] = PHASE_DONE
            logger.warning("灾变防线：试探走位达到上限仍未进门，交回主循环")
        else:
            _state["attempt"] = attempt + 1
            _state["phase"] = PHASE_RETRY
            _state["retry_until"] = now + retry_wait
            logger.info(f"灾变防线：第 {attempt}/{attempts} 次未进门，{retry_wait:.0f} 秒后再试")
        return True
