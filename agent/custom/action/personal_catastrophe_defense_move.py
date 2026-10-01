"""灾变防线：上半结束后的走位进传送门（个人版新增）。

灾变防线的战斗分上下半场，上半打完后要手动操作角色走到场地中央的传送门才能进下半。

【什么时候该走位：画面静止，而不是掐表】
上半场战斗中画面一直在动（角色、特效、伤害飘字）；上半场打完后游戏停下来等你
走位，画面只剩环境待机动画 —— 实测变化像素占比 1.3%~1.9% 且非常稳定。
判据就是「画面连续 still_seconds 秒变化都不大」。
正好走位节点是战斗循环 next 列表的最后一个（DirectHit 兜底），它被调用时就意味着
「命运卡片_拿走 / 选卡 / 点击空白处继续 / 挑战成功」全都没命中 —— 也就是用户说的
「不是命运卡选择、也不是点击空白处继续」，这两个条件由 pipeline 天然帮我们排除了。

三重保险，任意一条成立就开始走位：
  1. min_wait 秒之后，画面连续静止 still_seconds 秒（主判据）；
  2. max_wait 秒兜底强制开走（静止判据万一失灵也不至于干等）；
  3. 一轮没进门就回到等待，画面再次静止后重试（上半场没结束的话画面会重新动起来）。

按键：先按住 W+A 约 12 秒走向左上角，再按住 S+D 走向中央传送门。

【为什么调用必须快进快出（踩过的坑）】
CustomAction.run() 执行期间，整条 pipeline 都在等它返回 —— 它跑多久，战斗循环就
卡多久。上半场全程都在弹「命运卡片」，如果这个动作一进来就闷头等几分钟，卡片就
完全没人点了。所以：
  - 等待/静止检测阶段：每次调用只截一帧比一下，立刻返回，控制权交回战斗循环；
  - 真正走位的阶段：才连续按住方向键（此时画面已经静止，本来也没有卡片要点）。
每一步等待都检查 context.tasker.stopping，用户点停止能立刻响应。

【等待为什么不用 time.sleep】
CustomAction.run() 跑在 agent 的消息处理线程上，长时间 sleep 会让整个 agent
停止响应（客户端截图不再更新、任务停不掉）。等待全部用框架截图驱动
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

## 相邻两次取样间隔超过这么多秒就不比较（间隔太久，动态可能被平均掉）
SAMPLE_GAP_LIMIT = 3.0

## 抽帧步长（每隔几个像素取一个点），够用且快
SAMPLE_STRIDE = 4

## 变化率心跳日志间隔（秒）—— 实机调 still_ratio 的依据
RATIO_LOG_INTERVAL = 10.0

## 走位阶段
PHASE_WAIT = "wait"  ## 等画面静止 = 等上半场打完
PHASE_LEFT = "left"  ## 按住 W+A 走向左上角
PHASE_PORTAL = "portal"  ## 按住 S+D 走向中央传送门
PHASE_DONE = "done"  ## 已进门 / 已达上限

## 走位状态（由 reset 动作清零）
_state: dict = {}


def _reset_state() -> None:
    _state.clear()
    _state.update(
        started_at=None,
        force_at=0.0,
        phase=PHASE_WAIT,
        attempt=0,
        entered=False,
        last_gray=None,
        last_at=0.0,
        still_since=None,
        ratio_log_at=0.0,
    )


_reset_state()


def _grab(context: Context):
    """截一帧；失败返回 None。"""

    try:
        return context.tasker.controller.post_screencap().wait().get()
    except Exception:  # noqa: BLE001 - 任务停止时框架会拒绝截图
        return None


def _is_black(image) -> bool:
    """整屏平均亮度过低即认为在加载（黑屏）。"""

    if image is None or getattr(image, "size", 0) == 0:
        return False
    return float(np.asarray(image)[::SAMPLE_STRIDE, ::SAMPLE_STRIDE].mean()) < BLACK_MEAN_THRESHOLD


def _to_gray(image):
    """抽点 + 转灰度，返回 int16 二维数组。"""

    small = np.asarray(image)[::SAMPLE_STRIDE, ::SAMPLE_STRIDE]
    if small.ndim == 3:
        return small.astype(np.int16).mean(axis=2)
    return small.astype(np.int16)


def _update_stillness(image, now: float, still_seconds: float, still_ratio: float, pixel_diff: int) -> bool:
    """把这一帧和上一帧比一比，判断画面是否已经连续静止 still_seconds 秒。

    Returns:
        bool: True 表示画面够久了，可以开始走位。
    """

    if image is None or getattr(image, "size", 0) == 0:
        return False

    ## 加载黑屏是完全静止的，不能算「上半场结束」
    if _is_black(image):
        _state["last_gray"] = None
        _state["still_since"] = None
        return False

    gray = _to_gray(image)
    last = _state.get("last_gray")
    last_at = _state.get("last_at", 0.0)

    if last is not None and last.shape == gray.shape and (now - last_at) <= SAMPLE_GAP_LIMIT:
        ratio = float((np.abs(gray - last) > pixel_diff).mean())

        ## 限流心跳：把实测变化率写进日志，方便按实机数值调 still_ratio
        if now - _state.get("ratio_log_at", 0.0) >= RATIO_LOG_INTERVAL:
            _state["ratio_log_at"] = now
            counting = "，静止计时中" if _state.get("still_since") else ""
            logger.info(f"灾变防线：画面变化率 {ratio:.4f}（静止阈值 {still_ratio:.3f}{counting}）")

        if ratio < still_ratio:
            since = _state.get("still_since")
            if since is None:
                _state["still_since"] = now
                logger.info(f"灾变防线：画面已静止（变化率 {ratio:.4f}），持续 {still_seconds:.0f} 秒后开始试探走位")
            elif now - since >= still_seconds:
                _state["last_gray"] = gray
                _state["last_at"] = now
                return True
        else:
            if _state.get("still_since") is not None:
                logger.info(f"灾变防线：画面恢复变化（变化率 {ratio:.4f}），静止计时清零")
            _state["still_since"] = None

    _state["last_gray"] = gray
    _state["last_at"] = now
    return False


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
    """试探式走位进传送门：等画面静止再走，等待阶段秒回。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        if context.tasker.stopping or _state.get("entered"):
            return True

        node_data = context.get_node_data(argv.node_name) or {}
        attach = node_data.get("attach", {}) or {}
        min_wait = float(attach.get("min_wait", 120))
        still_seconds = float(attach.get("still_seconds", 8))
        still_ratio = float(attach.get("still_ratio", 0.05))
        pixel_diff = int(attach.get("pixel_diff", 16))
        max_wait = float(attach.get("max_wait", 330))
        left_seconds = float(attach.get("left_seconds", 12))
        portal_seconds = float(attach.get("portal_seconds", 5))
        attempts = int(attach.get("attempts", 8))

        now = time.time()

        ## 首次被调用：只记时间，立刻让战斗循环回去识别命运卡片
        if _state.get("started_at") is None:
            _state["started_at"] = now
            _state["force_at"] = now + max_wait
            _state["phase"] = PHASE_WAIT
            logger.info(
                f"灾变防线：进入战斗循环，{min_wait:.0f} 秒后开始检测画面静止"
                f"（静止 {still_seconds:.0f} 秒即走位，最长等 {max_wait:.0f} 秒）"
            )
            return True

        phase = _state.get("phase", PHASE_WAIT)

        ## 等上半场打完（画面静止）：本动作秒回，战斗循环每轮都会重新识别命运卡片
        if phase == PHASE_WAIT:
            elapsed = now - _state["started_at"]
            ready = _update_stillness(_grab(context), now, still_seconds, still_ratio, pixel_diff)

            ## 刚开始的一段时间不采信静止（避免上半场某段平静时误判）
            if elapsed < min_wait:
                _state["still_since"] = None
                ready = False

            ## 兜底：等太久了就强制开走一次；之后重新计一轮
            if not ready and max_wait > 0 and now >= _state.get("force_at", 0.0):
                _state["force_at"] = now + max_wait
                ready = True
                logger.warning(f"灾变防线：已等满 {max_wait:.0f} 秒画面仍未静止，强制开始试探走位")

            if ready:
                _state["phase"] = PHASE_LEFT
                _state["attempt"] = _state.get("attempt", 0) + 1
                logger.info(f"灾变防线：开始第 {_state['attempt']}/{attempts} 次试探走位")
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
            ## 回到「等画面静止」：若上半场其实没结束，画面会重新动起来，就继续等
            _state["phase"] = PHASE_WAIT
            _state["still_since"] = None
            _state["last_gray"] = None
            logger.info(f"灾变防线：第 {attempt}/{attempts} 次未进门，回到等待，画面再次静止后重试")
        return True
