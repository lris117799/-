# core/pokemon_data.py
import json
import os

# 图鉴数据库文件路径
POKEMON_DB_FILE = os.path.join(os.path.dirname(__file__), "pokemon_database.json")

# 用户自定义精灵文件路径
CUSTOM_POKEMON_FILE = os.path.join(os.path.dirname(__file__), "custom_pokemon.json")

def load_pokemon_database():
    """加载图鉴数据库"""
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

def get_all_pokemon():
    """获取所有精灵（图鉴 + 自定义）"""
    database = load_pokemon_database()
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
