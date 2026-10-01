<!-- markdownlint-disable MD033 MD041 -->

<div align="center">
    <img src="assets/logo.png" alt="StellaSora-Auto-Helper" width="200" />
    <h1>MaaStellaSora-Personal</h1>
    <p>星塔助手 个人版：以官方 MaaStellaSora 为基线的叠加式增强版，由 MaaFramework 强力驱动</p>
</div>

> **这是个人版（MaaStellaSora-Personal）**：基于[官方仓库](https://github.com/MaaStellaSora/MaaStellaSora)的叠加式增强版，
> 持续跟随上游更新。使用中遇到问题请提到**本仓库的 Issues**，不要打扰上游；差异、增量约定与同步流程见 [PERSONAL.md](PERSONAL.md)。

> ⚠ **下载请认准[本仓库的 Releases](https://github.com/beichen24a1/MaaStellaSora-Personal/releases)** —— 上游的发行包**不含**下面列出的个人版新增功能。

> 项目当前仍处于预览版，可能会遇到部分问题

## 功能

官方版已有的功能全部保留：

- [x] 登录游戏并签到
- [x] 清理活动
- [x] 赠礼
- [x] 五次邀约
- [x] 领取&发送好友干劲
- [x] 领取委托并重新派遣
- [x] 领取任务
- [x] 自动爬塔
- [x] 自动进行指定关卡
- [x] 真格挑战
- [x] 猎影合围

个人版新增：

- [x] **灾变防线** —— 自动完成当期挑战：选关 → 记录选择（两区域分别判断，已有纪录原样沿用）→ 前往挑战 → 上半场自动点命运卡片 → 画面静止后自动走位进传送门 → 下半场 → 挑战成功 → 领奖 → 返回主页

> **灾变防线的注意事项**：仅适配**桌面端**，不适配模拟器；且只在桌面端 **1280×720** 下测试过，其他分辨率可能导致识别与走位不稳定。
> 进入传送门需要模拟**真实键盘**（WASD），运行期间请保持游戏窗口在前台（别最小化或切后台，期间鼠标可能被短暂接管）。只打「灾变」难度，每期只能打一次。

## 安装与使用

> 星塔助手目前只对比例为16:9的游戏客户端提供支持，如果你的游戏客户端比例不为16:9请自行寻找改分辨率方法或是使用模拟器

1. 前往[本仓库的 Releases](https://github.com/beichen24a1/MaaStellaSora-Personal/releases)下载对应系统的压缩包。
2. 当前构建与发行使用 **MFAAvalonia**：下载 `MaaStellaSora-{系统}-{架构}-vX.Y.Z.zip`（Windows）或对应的 `.tar.gz`（Linux/macOS），支持现有全部发布平台及自动更新。
3. 将压缩包完整解压到独立目录，运行包内的 MFAAvalonia 主程序。
4. 如果需要操控 Windows 版《星塔旅人》，请使用管理员权限运行 GUI；使用 ADB 时可直接启动。

## 反馈与文档

本仓库是**个人版**，不接受外部贡献；遇到问题请提到本仓库的 Issues。

参考文档：[项目结构](docs/zh_cn/项目结构.md) · [Pipeline 编写规范](docs/zh_cn/Pipeline编写规范.md) · [个人版说明](PERSONAL.md)

## 鸣谢

本项目由 **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 强力驱动！

本项目部分功能使用 **[MaaPipelineEditor](https://github.com/kqcoxn/MaaPipelineEditor)** 进行辅助编辑

上游项目：[MaaStellaSora](https://github.com/MaaStellaSora/MaaStellaSora)

## 相关项目

- **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 基于图像识别的自动化黑盒测试框架
- **[MFAAvalonia](https://github.com/MaaXYZ/MFAAvalonia)** 基于 Avalonia 的通用 GUI，由 MaaFramework 强力驱动
- **[MXU](https://github.com/MistEO/MXU)** 基于 Web 技术的 MaaFramework 通用 GUI
- **[MaaPipelineEditor](https://github.com/kqcoxn/MaaPipelineEditor)** 可视化阅读与构建 Pipeline，功能完备，极致轻量跨平台，提供渐进式本地功能扩展，无缝兼容新旧项目
