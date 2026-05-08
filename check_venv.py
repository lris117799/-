import sys
import os

# 验证虚拟环境
venv_python = r"D:\game\lkwg\venv\Scripts\python.exe"

if os.path.exists(venv_python):
    print(f"✓ 虚拟环境存在: {venv_python}")
    
    # 测试导入PySide6
    import subprocess
    result = subprocess.run([venv_python, "-c", "import PySide6; print('PySide6:', PySide6.__version__)"], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ PySide6可用:", result.stdout.strip())
        print("\n虚拟环境完全正常！")
        print("请在PyCharm中手动选择此解释器路径:")
        print(venv_python)
    else:
        print("✗ PySide6不可用:", result.stderr)
else:
    print(f"✗ 虚拟环境不存在: {venv_python}")
