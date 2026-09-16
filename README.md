<!-- markdownlint-disable MD033 MD041 -->

<div align="center">
    <img src="assets/logo.png" alt="MaaStellaSora-Personal" width="200" />
    <h1>MaaStellaSora 个人版</h1>
    <p>只做一件事：自动爬塔</p>
</div>

> **这是个人自用改版**，从 [MaaStellaSora](https://github.com/MaaStellaSora/MaaStellaSora) v1.2.2 精简而来，
> 移除了签到、活动、赠礼、邀约、委托、采购、心链等**全部非爬塔功能**，任务列表只剩爬塔。
>
> 使用中遇到问题请提到**本仓库的 Issues**，不要去打扰官方项目。

## 功能

### 爬塔任务

| 任务 | 说明 |
| --- | --- |
| **预设爬塔** | 内置 4 套队伍的潜能优先级方案（水队_千多薇 / 暗队_花乙珂 / 光队_希火缇 / 火队_冬菈紫），选好队伍即可开跑 |
| **新版爬塔** | 完整自动爬塔流程，各项参数可自定义 |

### 潜能选择

- **优先级可指定**：给规则写 `priority` 直接决定排名（数字越小越优先，可为负数）；不写则沿用原来的列表行号
- **等级跃升提升**：一次能跃升多级的潜能自动提前（写了 `priority` 的规则才生效）
- **特殊机制识别**：暗·蜃影、礼炮双响、镜水归潮按等级跨度与刷新次数决定是否抓取
- **强化阶段跳过**：可标记某些潜能只在选择阶段要，强化阶段不选
- **未拥有优先**：优先级相同时，优先选还没拿过的潜能

### 停止条件

- **潜能数目标 / 记录等级目标**：结算时识别潜能数与记录等级，达到目标自动停止爬塔（填 0 表示不判断）

### 商店

- **音符购买策略**：可手动指定目标音符、只在最终商店补齐
- **音符数量目标**：为每种音符设定目标数量，符合折扣时买到目标数为止，够了就不再买

## 与原版（官方 MaaStellaSora）的区别

| | 官方版 | 本版 |
| --- | --- | --- |
| 功能范围 | 签到、活动、赠礼、邀约、委托、采购、心链、爬塔…… | **只有爬塔** |
| 潜能优先级 | 列表行号即排名 | 可写 `priority` 指定，含跃升提升 / 特殊机制 / 强化跳过 |
| 停止时机 | 刷满设定次数 | 可按潜能数、记录等级达标自动停止 |
| 商店音符 | 指定目标音符 | 增加每种音符的数量目标，按目标补齐 |

## 安装与使用

> 只支持比例为 **16:9** 的游戏客户端。比例不对请自行调整分辨率，或使用模拟器。

1. 前往 [Releases](https://github.com/beichen24a1/MaaStellaSora-Personal/releases) 下载 **MaaStellaSora-Personal-win-x86_64-v1.2.2.zip**（选带 Latest 标签的版本，不要选 Nightly / Alpha 等后缀）
2. 解压到任意目录（路径不要含特殊符号）
3. 需要时先运行 `依赖库安装.bat`
4. 操控 Windows 版星塔旅人时用**管理员身份**运行 `MFAAvalonia.exe`；用 ADB 连模拟器则直接启动即可
5. 任务列表里选择「预设爬塔」或「新版爬塔」，配置后启动

推荐的 Windows 包已经预配置好：关闭了启动时的版本检查与资源自动更新、界面语言设为简体中文，解压即用。

## 支持范围

- **服务器**：官服 / 台服 / 国际服 / 日服
- **连接方式**：桌面端（Win32）、安卓端（ADB）、PlayCover

## 说明

- 基于 **MaaStellaSora v1.2.2** 修改，遵循 **MIT** 协议，原项目版权归原作者所有
- 本仓库是个人自用改版，与官方项目无关；官方仓库见 [MaaStellaSora](https://github.com/MaaStellaSora/MaaStellaSora)
- 功能与资源均来自个人使用需求，不保证与官方版的更新同步

## 鸣谢

本项目由 **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 强力驱动！

- **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** —— 基于图像识别的自动化黑盒测试框架
- **[MFAAvalonia](https://github.com/SweetSmellFox/MFAAvalonia)** —— 基于 Avalonia 的通用 GUI
- **[MaaPipelineEditor](https://github.com/kqcoxn/MaaPipelineEditor)** —— 可视化阅读与构建 Pipeline
- **[MaaStellaSora](https://github.com/MaaStellaSora/MaaStellaSora)** —— 本项目的上游
