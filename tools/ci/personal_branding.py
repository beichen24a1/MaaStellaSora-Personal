"""发行包个人化：改可执行文件名、窗口标题与 Windows 文件图标。

发行包的外壳是 MFAAvalonia（MaaFramework 的通用 GUI），所以打包出来的可执行文件
一直叫 `MFAAvalonia.exe`、文件图标也是它的。本脚本在 `tools/ci/install.py` 之后、
把 MFA 文件合进 `install/` 之后运行，把这几处改成个人版的身份：

1. **改文件名**：`MFAAvalonia.exe` → `MaaStellaSora-Personal.exe`（Linux/macOS 无后缀）。
   .NET 的 apphost 里**硬编码**了它要加载的 <程序集名>.dll，与 exe 文件名无关，
   所以改名不影响启动（已核对二进制里确实嵌着 `MFAAvalonia.dll`）。
2. **改文件图标**：改写 PE 的 `RT_ICON` / `RT_GROUP_ICON` 资源，用仓库的 `assets/logo.ico`。
   只在 Windows 上做；窗口/任务栏图标本来就走 `Assets/logo.ico`，不受影响。
3. **改窗口标题**：把 `interface.json` 的 `custom_title` 从 install.py 写的
   `星塔助手<版本>` 改成 `MaaStellaSora-Personal <版本>`。

只用标准库（ctypes 直接调 Win32 资源 API），不依赖第三方打包工具。
"""

from __future__ import annotations

import ctypes
import json
import struct
import sys
from ctypes import wintypes
from pathlib import Path

APP_NAME = "MaaStellaSora-Personal"
OLD_EXECUTABLES = ("MFAAvalonia.exe", "MFAAvalonia")

RT_ICON = 3
RT_GROUP_ICON = 14
LANG_NEUTRAL = 0


def rename_executable(install_dir: Path) -> Path | None:
    """把 MFAAvalonia 的可执行文件改成 APP_NAME；找不到返回 None。"""

    for old_name in OLD_EXECUTABLES:
        source = install_dir / old_name
        if not source.is_file():
            continue
        new_name = APP_NAME + source.suffix
        target = install_dir / new_name
        if target.exists():
            target.unlink()
        source.rename(target)
        print(f"[branding] rename {old_name} -> {new_name}")
        return target
    print("[branding] warn: 没有找到 MFAAvalonia 可执行文件，跳过改名")
    return next(
        (
            install_dir / (APP_NAME + suffix)
            for suffix in (".exe", "")
            if (install_dir / (APP_NAME + suffix)).is_file()
        ),
        None,
    )


def rewrite_custom_title(install_dir: Path, version: str) -> None:
    """把发行态 interface.json 的窗口标题改成个人版。"""

    path = install_dir / "interface.json"
    if not path.is_file():
        print("[branding] warn: 没有找到 interface.json，跳过改标题")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["custom_title"] = f"{APP_NAME} {version}"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
    )
    print(f"[branding] custom_title -> {data['custom_title']}")


## ---------------------------------------------------------------- Windows 图标


def _load_ico(path: Path) -> list[dict]:
    """把 .ico 拆成每个尺寸的图像数据。"""

    data = path.read_bytes()
    _reserved, image_type, count = struct.unpack_from("<HHH", data, 0)
    if image_type != 1:
        raise ValueError(f"不是图标文件: {path}")
    entries: list[dict] = []
    offset = 6
    for _ in range(count):
        width, height, colors, _r, planes, bits, size, image_offset = struct.unpack_from(
            "<BBBBHHII", data, offset
        )
        entries.append(
            {
                "width": width or 256,
                "height": height or 256,
                "colors": colors,
                "planes": planes,
                "bits": bits,
                "image": data[image_offset : image_offset + size],
            }
        )
        offset += 16
    return entries


def _resource_ids(module: int, resource_type: int) -> list[int]:
    """列出某个资源类型下所有整数 ID。"""

    found: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HMODULE, wintypes.LPVOID, wintypes.LPVOID, wintypes.LPARAM
    )
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.EnumResourceNamesW.restype = wintypes.BOOL
    kernel32.EnumResourceNamesW.argtypes = [
        wintypes.HMODULE, wintypes.LPVOID, callback_type, wintypes.LPARAM,
    ]

    def _callback(_module, _type, name, _param):
        found.append(ctypes.cast(name, ctypes.c_void_p).value)
        return True

    kernel32.EnumResourceNamesW(
        module, ctypes.c_void_p(resource_type), callback_type(_callback), 0
    )
    return found


def set_windows_icon(exe: Path, ico: Path) -> None:
    """用 Win32 资源 API 把 exe 的文件图标换成 ico。"""

    if sys.platform != "win32":
        print("[branding] 非 Windows，跳过 PE 图标")
        return

    entries = _load_ico(ico)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.BeginUpdateResourceW.restype = wintypes.HANDLE
    kernel32.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
    kernel32.UpdateResourceW.restype = wintypes.BOOL
    kernel32.UpdateResourceW.argtypes = [
        wintypes.HANDLE, wintypes.LPVOID, wintypes.LPVOID,
        wintypes.WORD, wintypes.LPVOID, wintypes.DWORD,
    ]
    kernel32.EndUpdateResourceW.restype = wintypes.BOOL
    kernel32.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]

    ## 先读出原有资源 ID，删的时候要按真实 ID 删（MFA 的 GROUP_ICON 用的是 32512）
    kernel32.LoadLibraryExW.restype = wintypes.HMODULE
    kernel32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
    kernel32.FreeLibrary.restype = wintypes.BOOL
    kernel32.FreeLibrary.argtypes = [wintypes.HMODULE]
    module = kernel32.LoadLibraryExW(str(exe), None, 0x2)
    icon_ids: list[int] = []
    group_ids: list[int] = []
    if module:
        icon_ids = _resource_ids(module, RT_ICON)
        group_ids = _resource_ids(module, RT_GROUP_ICON)
        kernel32.FreeLibrary(module)

    handle = kernel32.BeginUpdateResourceW(str(exe), False)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        for resource_id in icon_ids:
            kernel32.UpdateResourceW(
                handle, ctypes.c_void_p(RT_ICON), ctypes.c_void_p(resource_id),
                LANG_NEUTRAL, None, 0,
            )
        for resource_id in group_ids:
            kernel32.UpdateResourceW(
                handle, ctypes.c_void_p(RT_GROUP_ICON), ctypes.c_void_p(resource_id),
                LANG_NEUTRAL, None, 0,
            )

        for index, entry in enumerate(entries, start=1):
            image = entry["image"]
            buffer = ctypes.create_string_buffer(image, len(image))
            if not kernel32.UpdateResourceW(
                handle, ctypes.c_void_p(RT_ICON), ctypes.c_void_p(index),
                LANG_NEUTRAL, buffer, len(image),
            ):
                raise ctypes.WinError(ctypes.get_last_error())

        group = struct.pack("<HHH", 0, 1, len(entries))
        for index, entry in enumerate(entries, start=1):
            group += struct.pack(
                "<BBBBHHIH",
                0 if entry["width"] >= 256 else entry["width"],
                0 if entry["height"] >= 256 else entry["height"],
                entry["colors"],
                0,
                entry["planes"],
                entry["bits"],
                len(entry["image"]),
                index,
            )
        group_buffer = ctypes.create_string_buffer(group, len(group))
        group_id = group_ids[0] if group_ids else 32512
        if not kernel32.UpdateResourceW(
            handle, ctypes.c_void_p(RT_GROUP_ICON), ctypes.c_void_p(group_id),
            LANG_NEUTRAL, group_buffer, len(group),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
    except BaseException:
        kernel32.EndUpdateResourceW(handle, True)
        raise
    if not kernel32.EndUpdateResourceW(handle, False):
        raise ctypes.WinError(ctypes.get_last_error())
    print(f"[branding] icon -> {exe.name} ({len(entries)} 个尺寸)")


def main(argv: list[str]) -> None:
    """argv: <install_dir> <version>"""

    if len(argv) != 3:
        raise SystemExit("用法: personal_branding.py <install_dir> <version>")
    install_dir = Path(argv[1]).resolve()
    version = argv[2]
    if not install_dir.is_dir():
        raise SystemExit(f"install_dir 不存在: {install_dir}")

    executable = rename_executable(install_dir)
    rewrite_custom_title(install_dir, version)
    if executable is not None:
        set_windows_icon(executable, Path(__file__).resolve().parents[2] / "assets" / "logo.ico")


if __name__ == "__main__":
    main(sys.argv)
