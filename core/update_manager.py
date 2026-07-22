# -*- coding: utf-8 -*-
"""
更新管理模块

负责：
- 检查 GitHub Releases 上的新版本
- 下载新版本 zip 包
- 应用更新（保留用户存档与设置文件）
- 通过批处理脚本重启程序

更新源：https://github.com/lris117799/-
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
import zipfile
from typing import Callable, Optional


# ──────────────────────────────────────────────────────────────
# 基础配置
# ──────────────────────────────────────────────────────────────
CURRENT_VERSION = "4.6.11"  # 当前程序版本号
GITHUB_OWNER = "lris117799"
GITHUB_REPO = "-"  # 仓库名称为 "-"


# 用户数据/设置文件白名单（更新时这些文件不会被覆盖）
# 路径相对于 klxy 程序根目录（即 dist/klxy/）
USER_PRESERVE_FILES = [
    # 设置文件
    os.path.join("core", "settings.json"),
    # 计数器数据
    os.path.join("core", "counters.json"),
    # 自定义精灵
    os.path.join("core", "custom_pokemons.json"),
    # 异色记录
    os.path.join("core", "shiny_records.json"),
    # 用户精灵数据库（s1/s2/s3）
    os.path.join("core", "pokemon_database.json"),
    os.path.join("core", "pokemon_database_s2.json"),
    os.path.join("core", "pokemon_database_s3.json"),
    # 根目录的 settings.json（兼容旧版）
    "settings.json",
    # 根目录的存档数据
    "owl_stars.json",
    "sheet_music.json",
    # 桌宠数据
    os.path.join("zc", "pet_data.json"),
    # 收集资源数据
    os.path.join("zy", "owl_stars.json"),
    os.path.join("zy", "sheet_music.json"),
    os.path.join("zy", "collect_resources_final.json"),
    os.path.join("zy", "internal_resource_point.json"),
    # 地图调试日志
    os.path.join("image", "map", "map_debug.log"),
]


def get_app_root_dir() -> str:
    """获取程序根目录（exe 所在目录 或 开发时项目根目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def compare_versions(v1: str, v2: str) -> int:
    """比较两个版本号（如 '4.6.8' 与 '4.7.0'）

    返回：
      1  如果 v1 > v2
      0  如果 v1 == v2
     -1  如果 v1 < v2
    """
    def _parse(v: str):
        parts = []
        for p in v.strip().lstrip("vV").split("."):
            try:
                parts.append(int(p))
            except ValueError:
                # 处理类似 4.6.8a 的情况
                num = ""
                for ch in p:
                    if ch.isdigit():
                        num += ch
                    else:
                        break
                parts.append(int(num) if num else 0)
        return parts

    a = _parse(v1)
    b = _parse(v2)
    # 补齐长度
    while len(a) < len(b):
        a.append(0)
    while len(b) < len(a):
        b.append(0)
    for x, y in zip(a, b):
        if x > y:
            return 1
        if x < y:
            return -1
    return 0


def get_latest_release(timeout: int = 15) -> Optional[dict]:
    """从 GitHub 获取最新 release 信息

    返回字典格式：
    {
        "tag_name": "v4.6.8",
        "name": "release 标题",
        "body": "更新日志正文",
        "html_url": "release 页面 URL",
        "assets": [{"name": "klxy.zip", "url": "...", "size": 123456}],
    }
    失败返回 None。
    """
    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    req = urllib.request.Request(api_url)
    req.add_header("User-Agent", "klxy-updater")
    req.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
        print(f"[UpdateManager] 获取最新 release 失败: {e}")
        return None

    assets = []
    for a in data.get("assets", []) or []:
        assets.append({
            "name": a.get("name", ""),
            "url": a.get("browser_download_url", ""),
            "size": a.get("size", 0),
        })

    return {
        "tag_name": data.get("tag_name", ""),
        "name": data.get("name", ""),
        "body": data.get("body", "") or "",
        "html_url": data.get("html_url", ""),
        "assets": assets,
    }


def find_update_zip_asset(release: dict) -> Optional[dict]:
    """从 release 中找到用于更新的 zip asset

    优先匹配 klxy*.zip，否则取第一个 .zip 文件。
    """
    assets = release.get("assets", []) or []
    # 优先：klxy 开头的 zip
    for a in assets:
        name = a.get("name", "").lower()
        if name.startswith("klxy") and name.endswith(".zip"):
            return a
    # 其次：任何 .zip
    for a in assets:
        if a.get("name", "").lower().endswith(".zip"):
            return a
    return None


def check_for_update(timeout: int = 15) -> Optional[dict]:
    """检查是否有新版本

    返回：
        有新版本时返回 dict:
        {
            "current_version": "4.6.8",
            "latest_version": "4.7.0",
            "changelog": "...",
            "html_url": "...",
            "download_url": "https://...",
            "download_size": 12345678,
        }
        无新版本或检查失败时返回 None
    """
    rel = get_latest_release(timeout=timeout)
    if not rel:
        return None

    latest = rel["tag_name"].lstrip("vV").strip()
    if not latest:
        return None

    if compare_versions(latest, CURRENT_VERSION) <= 0:
        return None  # 无新版本

    asset = find_update_zip_asset(rel)
    if not asset:
        # 没有可下载的 zip 包，仅提示用户去手动下载
        return {
            "current_version": CURRENT_VERSION,
            "latest_version": latest,
            "changelog": rel["body"],
            "html_url": rel["html_url"],
            "download_url": "",
            "download_size": 0,
        }

    return {
        "current_version": CURRENT_VERSION,
        "latest_version": latest,
        "changelog": rel["body"],
        "html_url": rel["html_url"],
        "download_url": asset["url"],
        "download_size": asset.get("size", 0),
    }


def download_file(url: str, dest_path: str,
                  progress_callback: Optional[Callable[[int, int], None]] = None,
                  timeout: int = 30) -> bool:
    """下载文件到指定路径

    Args:
        url: 文件 URL
        dest_path: 目标文件路径
        progress_callback: 回调函数 (downloaded_bytes, total_bytes)
                           total_bytes 为 -1 表示未知
        timeout: 超时秒数

    Returns:
        True 成功 / False 失败
    """
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "klxy-updater")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length", "-1") or "-1")
            if total < 0:
                total = -1
            downloaded = 0
            chunk = 64 * 1024  # 64KB
            with open(dest_path, "wb") as f:
                while True:
                    buf = resp.read(chunk)
                    if not buf:
                        break
                    f.write(buf)
                    downloaded += len(buf)
                    if progress_callback:
                        try:
                            progress_callback(downloaded, total)
                        except Exception:
                            pass
        return True
    except Exception as e:
        print(f"[UpdateManager] 下载失败: {e}")
        return False


def _build_user_preserve_set(app_root: str) -> set:
    """构造需要保留的文件绝对路径集合（同时考虑根目录与 _internal 目录）"""
    preserve = set()
    # 打包模式下用户文件可能在两个位置：
    # 1. <app_root>/_internal/... (与 exe 同级 _internal 内的数据文件)
    # 2. <app_root>/... (exe 同级，例如 settings.json 在外部时)
    # 开发模式下：<app_root>/...
    internal_dir = os.path.join(app_root, "_internal")
    has_internal = os.path.isdir(internal_dir)

    for rel_path in USER_PRESERVE_FILES:
        # 主路径
        p1 = os.path.normpath(os.path.join(app_root, rel_path))
        if os.path.exists(p1):
            preserve.add(p1)
        # 打包模式下的 _internal 路径
        if has_internal:
            p2 = os.path.normpath(os.path.join(internal_dir, rel_path))
            if os.path.exists(p2):
                preserve.add(p2)
    return preserve


def apply_update(zip_path: str = "", extract_dir: str = "", restart: bool = True) -> bool:
    """应用更新：从已解压目录或 zip 文件覆盖到程序目录，保留用户文件，可选重启

    流程：
    1. 创建一个临时批处理脚本 update.bat
    2. 脚本内容：
       - 等待当前 exe 退出
       - 如果传入 extract_dir，直接从该目录覆盖（程序内已解压完成）
         否则在 bat 内解压 zip 到临时目录
       - 把文件覆盖到程序目录（跳过用户保留文件）
       - 删除临时文件
       - 重启 klxy.exe
    3. 启动该批处理（独立进程）
    4. 当前程序退出（由调用方负责，建议用 os._exit(0) 强制退出）

    Args:
        zip_path: 已下载的更新 zip 文件路径（仅当 extract_dir 为空时在 bat 内解压）
        extract_dir: 程序内已解压的目录（优先使用，避免 bat 内解压无进度）
        restart: 是否在更新完成后重启程序

    Returns:
        True 表示更新流程已成功启动（不保证已完成）
        False 表示启动失败
    """
    app_root = get_app_root_dir()
    exe_name = "klxy.exe" if getattr(sys, 'frozen', False) else None

    # 决定源目录模式
    use_extract_dir = bool(extract_dir and os.path.isdir(extract_dir))
    if not use_extract_dir and not zip_path:
        print("[UpdateManager] apply_update 需要 extract_dir 或 zip_path")
        return False

    # 构造保留文件集合（绝对路径，规范化）
    preserve_set = _build_user_preserve_set(app_root)

    # 把保留集合序列化为分号分隔的字符串（批处理用）
    # 由于路径可能含空格、中文、等号等特殊字符，改用文件列表
    preserve_list_path = os.path.join(tempfile.gettempdir(), "klxy_preserve_list.txt")
    try:
        with open(preserve_list_path, "w", encoding="utf-8") as f:
            for p in sorted(preserve_set):
                f.write(p + "\n")
    except Exception as e:
        print(f"[UpdateManager] 写入保留文件列表失败: {e}")
        return False

    # 构造批处理脚本
    bat_path = os.path.join(tempfile.gettempdir(), "klxy_updater.bat")

    # exe 路径（重启用）
    exe_path = sys.executable if getattr(sys, 'frozen', False) else ""
    exe_dir = app_root

    # 是否重启
    restart_cmd = ""
    if restart and exe_name:
        restart_cmd = f'start "" "{exe_path}"'

    if use_extract_dir:
        # 新模式：程序内已解压完成，bat 只负责覆盖文件 + 重启
        src_dir = extract_dir
        bat_content = f"""@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo [klxy 更新器] 正在等待程序退出...
:wait_exit
tasklist /FI "IMAGENAME eq {exe_name}" 2>nul | find /I "{exe_name}" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_exit
)

echo [klxy 更新器] 正在应用更新...
powershell -NoProfile -Command "$root='{exe_dir}'; $src='{src_dir}'; $preserve=Get-Content '{preserve_list_path}' -ErrorAction SilentlyContinue; $preserveSet=@{{}}; if ($preserve) {{ foreach ($p in $preserve) {{ $pp=$p.Trim(); if ($pp) {{ $preserveSet[$pp]=$true }} }} }}; Get-ChildItem -Path $src -Recurse -File | ForEach-Object {{ $rel=$_.FullName.Substring($src.Length+1); $dest=Join-Path $root $rel; $destNorm=([System.IO.Path]::GetFullPath($dest)).TrimEnd('\\'); if ($preserveSet.ContainsKey($destNorm)) {{ Write-Host ('SKIP: ' + $rel); return }}; $dir=Split-Path $dest -Parent; if (!(Test-Path $dir)) {{ New-Item -ItemType Directory -Path $dir -Force | Out-Null }}; Copy-Item -Path $_.FullName -Destination $dest -Force; Write-Host ('OK: ' + $rel) }}"

echo [klxy 更新器] 清理临时文件...
rmdir /S /Q "{src_dir}" 2>nul
del "{preserve_list_path}" 2>nul
{f'del "{zip_path}" 2>nul' if zip_path else ''}

echo [klxy 更新器] 更新完成！
{restart_cmd}
exit
"""
    else:
        # 旧模式：bat 内解压 zip（兼容路径，不推荐，无解压进度）
        qzip = f'"{zip_path}"'
        bat_content = f"""@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo [klxy 更新器] 正在等待程序退出...
:wait_exit
tasklist /FI "IMAGENAME eq {exe_name}" 2>nul | find /I "{exe_name}" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_exit
)

echo [klxy 更新器] 正在解压更新包...
set "TMP_DIR=%TEMP%\\klxy_update_extract"
if exist "%TMP_DIR%" rmdir /S /Q "%TMP_DIR%"
mkdir "%TMP_DIR%"

powershell -NoProfile -Command "Expand-Archive -Path {qzip} -DestinationPath '%TMP_DIR%' -Force"
if errorlevel 1 (
    echo [klxy 更新器] 解压失败！
    pause
    exit /b 1
)

echo [klxy 更新器] 正在应用更新...
powershell -NoProfile -Command "$root='{exe_dir}'; $preserve=Get-Content '{preserve_list_path}' -ErrorAction SilentlyContinue; $preserveSet=@{{}}; if ($preserve) {{ foreach ($p in $preserve) {{ $pp=$p.Trim(); if ($pp) {{ $preserveSet[$pp]=$true }} }} }}; Get-ChildItem -Path '%TMP_DIR%' -Recurse -File | ForEach-Object {{ $rel=$_.FullName.Substring('%TMP_DIR%'.Length+1); $dest=Join-Path $root $rel; $destNorm=([System.IO.Path]::GetFullPath($dest)).TrimEnd('\\'); if ($preserveSet.ContainsKey($destNorm)) {{ Write-Host ('SKIP: ' + $rel); return }}; $dir=Split-Path $dest -Parent; if (!(Test-Path $dir)) {{ New-Item -ItemType Directory -Path $dir -Force | Out-Null }}; Copy-Item -Path $_.FullName -Destination $dest -Force; Write-Host ('OK: ' + $rel) }}"

echo [klxy 更新器] 清理临时文件...
rmdir /S /Q "%TMP_DIR%" 2>nul
del "{preserve_list_path}" 2>nul
del "{zip_path}" 2>nul

echo [klxy 更新器] 更新完成！
{restart_cmd}
exit
"""

    try:
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
    except Exception as e:
        print(f"[UpdateManager] 写入批处理脚本失败: {e}")
        return False

    # 启动批处理（独立进程）
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "/min", bat_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
            close_fds=True,
        )
    except Exception as e:
        print(f"[UpdateManager] 启动更新脚本失败: {e}")
        return False

    return True
