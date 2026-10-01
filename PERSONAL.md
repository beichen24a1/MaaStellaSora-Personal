# 个人版说明（MaaStellaSora-Personal）

本仓库是 [MaaStellaSora](https://github.com/MaaStellaSora/MaaStellaSora) 的**个人版**：
以官方仓库为基线，在其之上叠加个人增量，并持续跟随上游更新。

## 与上游的关系

- **基线**：官方 `MaaStellaSora/MaaStellaSora` 的完整历史。本仓库的 `main` 默认与上游同构，
  上游每次发版都会合并进来（修复与新功能默认全收）。
- **增量**：个人自用的增强与适配，全部以**新增文件**的形式叠加，见下方约定。
- **原则**：不重写框架、不改上游节点与任务标识，保证"上游一发版，一次 merge 就能跟上"。

## 增量约定

1. **唯一允许修改的上游文件**：`assets/interface.json`
   - 身份字段（`name` / `github` / `description` / `welcome` 等）
   - `import` 数组追加个人任务文件
2. **个人增量一律新增文件**，命名带 `personal` 标识：
   - `agent/custom/action/personal_*.py`（并在 `agent/custom/action/__init__.py` 注册）
   - `agent/custom/reco/*_personal_*.py`
   - `assets/interface/tasks/personal_*.json`
   - `assets/resource/base/pipeline/common/personal_*.json`
   - `assets/resource/base/image/personal/*.png`
3. **新增 pipeline 文件必须放在 `base/pipeline/common/`（或 `climb_tower/`）下**，不能自建顶层目录。
   打开发行包时 `tools/ci/resource_layout.py` 会把 pipeline 重排成兼容既有客户端的布局：
   相对路径命中 `PIPELINE_PATHS` 表的会被摊平到 pipeline 根，其余只有首层目录是 `common` 或
   `climb_tower` 才放行，别的顶层目录会直接让整个构建失败：

   ```
   ValueError: unmapped pipeline file: assets/resource/base/pipeline/<你的目录>/xxx.json
   ```

   本地可以先这样验证，不用等 CI：

   ```python
   from pathlib import Path
   import tempfile
   from tools.ci.resource_layout import copy_resources
   copy_resources(Path("assets/resource"), Path(tempfile.mkdtemp()))
   ```
4. **禁止**重命名或删除上游节点、任务与选项标识 —— 外部工具（如 AUTO-MAS）按 `entry` 与选项名对接，
   改名会连带失效。

## 同步上游

```powershell
git fetch upstream
git log --oneline HEAD..upstream/main     # 上游新增了什么
git diff HEAD...upstream/main --stat      # 影响面
git merge upstream/main                   # 冲突应只出现在 assets/interface.json
```

## 发行包

必须走仓库自带的打包流程（`.github/workflows/install.yml` → `tools/ci/install.py`），
**不要手工修改发行包**。打包时会把源码态 `assets/interface.json` 提升到包根并改写：

| 字段 | 源码态 | 发行态 |
| --- | --- | --- |
| `version` | 占位值 | 打包时注入 Release 版本 |
| `agent.child_exec` | `python` | `./python/python.exe`（按平台） |
| `agent.child_args` | `["-u", "./../agent/main.py"]` | `["-u", "./agent/main.py"]` |

> 手工打包容易漏掉这步改写，包里的 `interface.json` 会停留在源码态，
> 在 AUTO-MAS 等内嵌运行的客户端里会因 agent 路径错误而启动失败。

## 在 AUTO-MAS 中使用

本版在 [AUTO-MAS](https://github.com/AUTO-MAS-Project/AUTO-MAS) 中与官方版同样是 `MSS`（星塔旅人）
类型，可直接作为「托管 MaaFramework 项目」导入；活动优先、计划表、周常编排等能力按项目身份识别。

## 问题反馈

请提到**本仓库的 Issues**，不要去打扰上游。
