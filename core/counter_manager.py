# core/counter_manager.py
from dataclasses import dataclass, field
from typing import List
import json
import os

@dataclass
class Counter:
    id: str
    pokemon_name: str
    counter_name: str
    type: str
    count: int = 0
    target: int = 80            # 保底次数
    base_prob: float = 1.8      # 基础异色概率
    is_custom: bool = False     # 是否为用户自定义
    is_locked: bool = False     # 是否锁定计数
    nightmare_count: int = 0    # 污染提示计数

    def current_probability(self):
        """动态概率（随着次数增加略微提升）"""
        bonus = self.count * 0.02  # 每破盾一次增加0.02%概率
        return min(100.0, self.base_prob + bonus)

    def progress_percent(self):
        return (self.count / self.target) * 100

class CounterManager:
    def __init__(self):
        self.counters: List[Counter] = []
        self.active_id: str = None
        self.is_folded: bool = False  # 折叠状态
        self.pokemon_breakthrough_stats: dict = {}  # 全局追踪数据 {精灵名: 击破次数}
        self.last_save_time: dict = {}  # 记录每个计数器上次保存的时间 {counter_id: timestamp}
        self.custom_pokemons_file = os.path.join(os.path.dirname(__file__), "custom_pokemons.json")
        self.counters_file = os.path.join(os.path.dirname(__file__), "counters.json")
        self.custom_pokemons = self._load_custom_pokemons()  # 自定义精灵列表
        self.load_counters()  # 启动时加载计数器数据

    def add_counter(self, pokemon_name: str, counter_name: str, type: str, is_custom: bool = False):
        new_id = f"c{len(self.counters)+1}_{pokemon_name}"
        counter = Counter(id=new_id, pokemon_name=pokemon_name, counter_name=counter_name, type=type, is_custom=is_custom)
        self.counters.append(counter)
        if self.active_id is None:
            self.active_id = new_id
        return counter

    def delete_counter(self, counter_id: str):
        self.counters = [c for c in self.counters if c.id != counter_id]
        if self.active_id == counter_id:
            self.active_id = self.counters[0].id if self.counters else None

    def get_active(self):
        for c in self.counters:
            if c.id == self.active_id:
                return c
        return None

    def set_active(self, counter_id: str):
        self.active_id = counter_id

    def modify_count(self, delta: int):
        active = self.get_active()
        if active and not active.is_locked:
            active.count = max(0, min(active.target, active.count + delta))
    
    def toggle_lock(self, counter_id: str = None):
        """切换锁定状态"""
        if counter_id:
            for c in self.counters:
                if c.id == counter_id:
                    c.is_locked = not c.is_locked
                    return c.is_locked
        else:
            active = self.get_active()
            if active:
                active.is_locked = not active.is_locked
                return active.is_locked
        return False

    def rename_counter(self, counter_id: str, new_name: str):
        for c in self.counters:
            if c.id == counter_id:
                c.counter_name = new_name
                break

    def toggle_pin(self, counter_id: str):
        """置顶：将该计数器移到列表第一个"""
        for i, c in enumerate(self.counters):
            if c.id == counter_id:
                self.counters.insert(0, self.counters.pop(i))
                break
    
    def toggle_fold(self):
        """切换折叠状态"""
        self.is_folded = not self.is_folded
        return self.is_folded
    
    # ================= 全局追踪功能 =================
    def add_global_breakthrough(self, pokemon_name: str):
        """增加全局污染击破计数"""
        if pokemon_name:
            self.pokemon_breakthrough_stats[pokemon_name] = self.pokemon_breakthrough_stats.get(pokemon_name, 0) + 1
    
    def get_global_breakthrough(self, pokemon_name: str) -> int:
        """获取全局污染击破计数"""
        return self.pokemon_breakthrough_stats.get(pokemon_name, 0)
    
    def remove_global_breakthrough(self, pokemon_name: str):
        """移除某个精灵的全局追踪数据（用于同步到计数器后）"""
        if pokemon_name in self.pokemon_breakthrough_stats:
            del self.pokemon_breakthrough_stats[pokemon_name]
    
    def clear_global_stats(self):
        """清空所有全局追踪数据"""
        self.pokemon_breakthrough_stats.clear()
    
    def get_all_global_stats(self) -> dict:
        """获取所有全局追踪数据"""
        return self.pokemon_breakthrough_stats.copy()
    
    def should_auto_save(self, counter_id: str, interval_minutes: int) -> bool:
        """检查是否应该自动保存
        
        Args:
            counter_id: 计数器ID
            interval_minutes: 自动保存间隔（分钟）
        
        Returns:
            bool: 是否应该保存
        """
        import time
        current_time = time.time()
        last_time = self.last_save_time.get(counter_id, 0)
        
        # 如果超过指定间隔，返回True
        if current_time - last_time >= interval_minutes * 60:
            return True
        return False
    
    def update_save_time(self, counter_id: str):
        """更新计数器的上次保存时间"""
        import time
        self.last_save_time[counter_id] = time.time()
    
    def _load_custom_pokemons(self):
        """加载自定义精灵列表"""
        if os.path.exists(self.custom_pokemons_file):
            try:
                with open(self.custom_pokemons_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_custom_pokemon(self, name: str, type_: str, evolution_chain: list = None, icon_id: int = 0):
        """保存自定义精灵到图鉴"""
        # 检查是否已存在
        for p in self.custom_pokemons:
            if p['name'] == name:
                return False
        
        pokemon_data = {'name': name, 'type': type_, 'is_custom': True}
        if icon_id > 0:
            pokemon_data['icon_id'] = icon_id
        if evolution_chain and len(evolution_chain) > 0:
            pokemon_data['evolution_chain'] = evolution_chain
        
        self.custom_pokemons.append(pokemon_data)
        with open(self.custom_pokemons_file, 'w', encoding='utf-8') as f:
            json.dump(self.custom_pokemons, f, ensure_ascii=False, indent=2)
        
        # 同步到EvolutionManager（如果可用）
        if hasattr(self, 'evolution_manager') and self.evolution_manager:
            self.evolution_manager.add_custom_pokemon(name, evolution_chain)
        
        return True
    
    def delete_custom_pokemon(self, name: str):
        """删除自定义精灵"""
        # 找到要删除的精灵，获取其进化链
        target_pokemon = None
        for p in self.custom_pokemons:
            if p['name'] == name:
                target_pokemon = p
                break
        
        if target_pokemon:
            evolution_chain = target_pokemon.get('evolution_chain', [])
            self.custom_pokemons = [p for p in self.custom_pokemons if p['name'] != name]
            with open(self.custom_pokemons_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_pokemons, f, ensure_ascii=False, indent=2)
            
            # 同步从EvolutionManager移除
            if hasattr(self, 'evolution_manager') and self.evolution_manager:
                self.evolution_manager.remove_custom_pokemon(name, evolution_chain)
    
    def update_custom_pokemon(self, old_name: str, new_name: str, new_type: str, new_icon: str):
        """更新自定义精灵"""
        for p in self.custom_pokemons:
            if p['name'] == old_name:
                p['name'] = new_name
                p['type'] = new_type
                p['icon'] = new_icon
                break
        with open(self.custom_pokemons_file, 'w', encoding='utf-8') as f:
            json.dump(self.custom_pokemons, f, ensure_ascii=False, indent=2)
    
    def get_custom_pokemons(self):
        """获取自定义精灵列表"""
        return self.custom_pokemons
    
    def save_counters(self):
        """保存计数器数据到文件"""
        data = {
            'active_id': self.active_id,
            'is_folded': self.is_folded,
            'counters': [
                {
                    'id': c.id,
                    'pokemon_name': c.pokemon_name,
                    'counter_name': c.counter_name,
                    'type': c.type,
                    'count': c.count,
                    'target': c.target,
                    'base_prob': c.base_prob,
                    'is_custom': c.is_custom,
                    'is_locked': c.is_locked,
                    'nightmare_count': c.nightmare_count
                }
                for c in self.counters
            ],
            'pokemon_breakthrough_stats': self.pokemon_breakthrough_stats  # 保存全局追踪数据
        }
        with open(self.counters_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_counters(self):
        """从文件加载计数器数据"""
        if not os.path.exists(self.counters_file):
            return
        
        try:
            with open(self.counters_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.active_id = data.get('active_id')
            self.is_folded = data.get('is_folded', False)
            self.pokemon_breakthrough_stats = data.get('pokemon_breakthrough_stats', {})  # 加载全局追踪数据
            
            self.counters = []
            for c_data in data.get('counters', []):
                counter = Counter(
                    id=c_data['id'],
                    pokemon_name=c_data['pokemon_name'],
                    counter_name=c_data['counter_name'],
                    type=c_data['type'],
                    count=c_data.get('count', 0),
                    target=c_data.get('target', 80),
                    base_prob=c_data.get('base_prob', 1.8),
                    is_custom=c_data.get('is_custom', False),
                    is_locked=c_data.get('is_locked', False),
                    nightmare_count=c_data.get('nightmare_count', 0)
                )
                self.counters.append(counter)
        except Exception as e:
            print(f"加载计数器数据失败: {e}")
