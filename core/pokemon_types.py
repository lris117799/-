# core/pokemon_types.py
"""
洛克王国精灵属性库 - 全局唯一数据源
"""

# 所有游戏内存在的属性（完整名称，带"系"字）
POKEMON_TYPES = [
    "普通系",
    "火系",
    "水系",
    "草系",
    "电系",
    "冰系",
    "武系",
    "毒系",
    "翼系",
    "萌系",
    "虫系",
    "地系",
    "幽灵系",
    "龙系",
    "恶魔系",
    "机械系",
    "光系",
    "幻系"
]

# 属性简称映射（用于显示或搜索）
TYPE_SHORT_NAMES = {
    "普通系": "普通",
    "火系": "火",
    "水系": "水",
    "草系": "草",
    "电系": "电",
    "冰系": "冰",
    "武系": "武",
    "毒系": "毒",
    "翼系": "翼",
    "萌系": "萌",
    "虫系": "虫",
    "地系": "地",
    "幽灵系": "幽灵",
    "龙系": "龙",
    "恶魔系": "恶魔",
    "机械系": "机械",
    "光系": "光",
    "幻系": "幻"
}


def get_all_types():
    """获取所有属性列表"""
    return POKEMON_TYPES.copy()


def get_type_display_name(full_type):
    """获取属性的显示名称（简称）"""
    return TYPE_SHORT_NAMES.get(full_type, full_type)


def normalize_type(type_name):
    """
    标准化属性名称
    如果输入的是简称，转换为完整名称
    """
    # 先检查是否已经是完整名称
    if type_name in POKEMON_TYPES:
        return type_name
    
    # 尝试匹配简称
    for full_name, short_name in TYPE_SHORT_NAMES.items():
        if type_name == short_name or type_name in short_name:
            return full_name
    
    return type_name
