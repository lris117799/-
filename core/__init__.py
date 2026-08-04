"""
Core module - 核心功能模块

包含：
- CircleSelector: 圆形框选工具
- GameCapture: 游戏画面捕获
- 其他工具类
"""

# from .game_recognizer import GameRecognizer  # 暂未实现
from .circle_selector import CircleSelector
from .game_capture import GameCapture, ScreenshotWorker, NightmareWorker
from .logger import logger
from .settings_manager import SettingsManager
from .counter_manager import CounterManager, Counter
from .evolution_manager import EvolutionManager
from .pokemon_data import POKEMON_LIST, get_all_pokemon, save_custom_pokemon, load_custom_pokemon
from .pokemon_types import get_all_types

__all__ = [
    # 'GameRecognizer',  # 暂未实现
    'CircleSelector',
    'GameCapture',
    'ScreenshotWorker',
    'NightmareWorker',
    'logger',
    'SettingsManager',
    'CounterManager',
    'Counter',
    'EvolutionManager',
    'POKEMON_LIST',
    'get_all_pokemon',
    'save_custom_pokemon',
    'load_custom_pokemon',
    'get_all_types'
]