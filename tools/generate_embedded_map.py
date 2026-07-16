# -*- coding: utf-8 -*-
"""将 image/map_full_hq.png 嵌入为 Python 模块（打包进 exe 内部）

生成结果:
    core/_map_data/__init__.py       - 加载入口，提供 get_map_bytes()
    core/_map_data/_chunk_000.py     - base64 分块数据
    core/_map_data/_chunk_001.py
    ...

打包后即使删除 _internal/image/map_full_hq.png，exe 仍可正常显示地图。

用法:
    python tools/generate_embedded_map.py
"""
import base64
import os
import sys
import shutil

# ── 配置 ──
SOURCE_PNG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "image", "map_full_hq.png")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "core", "_map_data")
# 每个分块的原始字节数（base64 后约增大 33%）
CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB


def main():
    if not os.path.exists(SOURCE_PNG):
        print(f"[ERROR] 源文件不存在: {SOURCE_PNG}")
        sys.exit(1)

    file_size = os.path.getsize(SOURCE_PNG)
    print(f"[INFO] 源文件: {SOURCE_PNG}")
    print(f"[INFO] 文件大小: {file_size / 1024 / 1024:.1f} MB")

    # 清理旧的生成目录
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # 读取并分块 base64 编码
    chunk_count = 0
    total_b64_size = 0
    with open(SOURCE_PNG, "rb") as f:
        while True:
            raw = f.read(CHUNK_SIZE)
            if not raw:
                break
            b64 = base64.b64encode(raw)
            chunk_file = os.path.join(OUTPUT_DIR, f"_chunk_{chunk_count:03d}.py")
            with open(chunk_file, "w", encoding="utf-8") as cf:
                cf.write(f"# 自动生成: map_full_hq.png 分块 {chunk_count:03d} (请勿手动编辑)\n")
                cf.write(f"CHUNK = {b64!r}\n")
            total_b64_size += len(b64)
            chunk_count += 1
            print(f"[INFO] 已生成分块 {chunk_count:03d} ({len(b64) / 1024 / 1024:.1f} MB)")

    # 生成 __init__.py（使用显式导入，确保 PyInstaller 能正确收集）
    import_lines = [
        '"""自动生成: 内嵌 map_full_hq.png 数据 (请勿手动编辑)',
        '',
        '由 tools/generate_embedded_map.py 生成。',
        '打包后此模块会被编译进 PYZ (位于 exe 内部)，',
        '即使删除 _internal/image/map_full_hq.png 仍可正常使用地图。',
        '"""',
        'import base64',
        '',
    ]
    # 显式导入每个分块（PyInstaller 的导入分析能追踪到这些）
    for i in range(chunk_count):
        import_lines.append(f'from ._chunk_{i:03d} import CHUNK as _chunk_{i:03d}')

    import_lines += [
        '',
        f'_CHUNK_COUNT = {chunk_count}',
        '',
        '',
        'def get_map_bytes():',
        '    """返回 map_full_hq.png 的原始 PNG 字节"""',
        '    chunks = [',
    ]
    for i in range(chunk_count):
        comma = ',' if i < chunk_count - 1 else ''
        import_lines.append(f'        base64.b64decode(_chunk_{i:03d}){comma}')
    import_lines += [
        '    ]',
        '    return b"".join(chunks)',
        '',
        '',
        'def has_embedded_map():',
        '    """是否已嵌入地图数据"""',
        '    return True',
        '',
        '',
        '# 模块列表，供 PyInstaller 收集',
        f'_all_chunk_modules = [f"core._map_data._chunk_{{i:03d}}" for i in range({chunk_count})]',
    ]
    with open(os.path.join(OUTPUT_DIR, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("\n".join(import_lines) + "\n")

    print(f"\n[OK] 生成完成:")
    print(f"     分块数量: {chunk_count}")
    print(f"     Base64 总大小: {total_b64_size / 1024 / 1024:.1f} MB")
    print(f"     输出目录: {OUTPUT_DIR}")
    print(f"\n[提示] 打包时 klxy.spec 会自动收集 core._map_data 的所有子模块")


if __name__ == "__main__":
    main()
