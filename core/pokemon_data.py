# core/pokemon_data.py
import json
import os

# 图鉴数据库文件路径
POKEMON_DB_FILE = os.path.join(os.path.dirname(__file__), "pokemon_database.json")
POKEMON_DB_FILE_S2 = os.path.join(os.path.dirname(__file__), "pokemon_database_s2.json")
POKEMON_DB_FILE_S3 = os.path.join(os.path.dirname(__file__), "pokemon_database_s3.json")

# 用户自定义精灵文件路径
CUSTOM_POKEMON_FILE = os.path.join(os.path.dirname(__file__), "custom_pokemons.json")

# 当前赛季
CURRENT_SEASON = "第三赛季"  # "第一赛季" 或 "第二赛季" 或 "第三赛季"

def set_current_season(season):
    """设置当前赛季"""
    global CURRENT_SEASON
    CURRENT_SEASON = season

def get_current_season():
    """获取当前赛季"""
    return CURRENT_SEASON

def get_seasons():
    """获取所有赛季列表"""
    return ["第一赛季", "第二赛季", "第三赛季"]

def load_pokemon_database(season=None):
    """加载图鉴数据库（支持赛季选择）"""
    if season is None:
        season = CURRENT_SEASON
    
    if season == "第三赛季" and os.path.exists(POKEMON_DB_FILE_S3):
        try:
            with open(POKEMON_DB_FILE_S3, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    elif season == "第二赛季" and os.path.exists(POKEMON_DB_FILE_S2):
        try:
            with open(POKEMON_DB_FILE_S2, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    else:
        if os.path.exists(POKEMON_DB_FILE):
            try:
                with open(POKEMON_DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
    return []

def load_custom_pokemon():
    """加载用户自定义的精灵"""
    if os.path.exists(CUSTOM_POKEMON_FILE):
        try:
            with open(CUSTOM_POKEMON_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_custom_pokemon(pokemon_list):
    """保存用户自定义的精灵"""
    with open(CUSTOM_POKEMON_FILE, 'w', encoding='utf-8') as f:
        json.dump(pokemon_list, f, ensure_ascii=False, indent=2)

def get_all_pokemon(season=None):
    """获取所有精灵（图鉴 + 自定义）"""
    database = load_pokemon_database(season)
    custom = load_custom_pokemon()
    return database + custom

# 向后兼容 - 动态获取最新数据
class PokemonListWrapper:
    def __getitem__(self, key):
        return get_all_pokemon()[key]
    
    def __iter__(self):
        return iter(get_all_pokemon())
    
    def __len__(self):
        return len(get_all_pokemon())

POKEMON_LIST = PokemonListWrapper()