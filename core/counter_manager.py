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
    nightmare_count: int = 0    # 童话事件计数
    icon_id: int = 0            # 精灵图标ID
    battle_pokemon_stats: dict = field(default_factory=dict)  # 童话事件期间出现的精灵统计 {精灵名: 出现次数}
    breakthrough_notified: bool = False  # 是否已发送保底通知

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
        self.shiny_records: List[dict] = []  # 出闪记录列表
        self._next_id: int = 1  # 自增ID计数器，确保每个计数器ID唯一
        
        self.custom_pokemons_file = os.path.join(os.path.dirname(__file__), "custom_pokemons.json")
        self.counters_file = os.path.join(os.path.dirname(__file__), "counters.json")
        self.shiny_records_file = os.path.join(os.path.dirname(__file__), "shiny_records.json")
        self.custom_pokemons = self._load_custom_pokemons()  # 自定义精灵列表
        self.load_counters()  # 启动时加载计数器数据
        self.load_shiny_records()  # 加载出闪记录

    def _generate_unique_id(self, pokemon_name: str) -> str:
        """生成唯一计数器ID，即使删除计数器后也不会重复"""
        new_id = f"c{self._next_id}_{pokemon_name}"
        self._next_id += 1
        return new_id

    def add_counter(self, pokemon_name: str, counter_name: str, type: str, is_custom: bool = False, icon_id: int = 0):
        new_id = self._generate_unique_id(pokemon_name)
        counter = Counter(id=new_id, pokemon_name=pokemon_name, counter_name=counter_name, type=type, is_custom=is_custom, icon_id=icon_id)
        self.counters.append(counter)
        self.active_id = new_id  # 创建后自动激活
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

    def navigate_counter(self, direction: int):
        """切换活跃计数器
        :param direction: +1=下一个, -1=上一个
        :return: 切换后的活跃计数器 或 None
        """
        if not self.counters:
            return None
        current = self.get_active()
        if current is None:
            self.active_id = self.counters[0].id
            return self.counters[0]
        for i, c in enumerate(self.counters):
            if c.id == current.id:
                new_idx = (i + direction) % len(self.counters)
                self.active_id = self.counters[new_idx].id
                return self.counters[new_idx]
        return None

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
        """增加全局童话事件计数"""
        if pokemon_name:
            self.pokemon_breakthrough_stats[pokemon_name] = self.pokemon_breakthrough_stats.get(pokemon_name, 0) + 1
    
    def get_global_breakthrough(self, pokemon_name: str) -> int:
        """获取全局童话事件计数"""
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
            'next_id': self._next_id,
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
                    'nightmare_count': c.nightmare_count,
                    'battle_pokemon_stats': c.battle_pokemon_stats,
                    'breakthrough_notified': c.breakthrough_notified
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
            
            # 加载 _next_id，并确保大于所有已有计数器ID中的数字
            saved_next_id = data.get('next_id', 1)
            self._next_id = saved_next_id
            
            self.counters = []
            seen_ids = set()
            for c_data in data.get('counters', []):
                cid = c_data['id']
                # 修复重复ID：如果ID已存在，生成新ID
                if cid in seen_ids:
                    old_id = cid
                    cid = self._generate_unique_id(c_data['pokemon_name'])
                    # 如果 active_id 指向了被重命名的旧ID，更新为新的ID
                    if self.active_id == old_id:
                        self.active_id = cid
                seen_ids.add(cid)
                
                # 从已有ID中提取数字，确保 _next_id 大于所有已有ID
                try:
                    num = int(cid.split('_')[0][1:])
                    self._next_id = max(self._next_id, num + 1)
                except:
                    pass
                
                counter = Counter(
                    id=cid,
                    pokemon_name=c_data['pokemon_name'],
                    counter_name=c_data['counter_name'],
                    type=c_data['type'],
                    count=c_data.get('count', 0),
                    target=c_data.get('target', 80),
                    base_prob=c_data.get('base_prob', 1.8),
                    is_custom=c_data.get('is_custom', False),
                    is_locked=c_data.get('is_locked', False),
                    nightmare_count=c_data.get('nightmare_count', 0),
                    battle_pokemon_stats=c_data.get('battle_pokemon_stats', {}),
                    breakthrough_notified=c_data.get('breakthrough_notified', False)
                )
                self.counters.append(counter)
            
            # 确保 active_id 有效（指向实际存在的计数器）
            if self.active_id and not any(c.id == self.active_id for c in self.counters):
                self.active_id = self.counters[0].id if self.counters else None
        except Exception as e:
            print(f"加载计数器数据失败: {e}")
    
    # ================= 出闪记录功能 =================
    def save_shiny_records(self):
        """保存出闪记录到文件"""
        try:
            with open(self.shiny_records_file, 'w', encoding='utf-8') as f:
                json.dump(self.shiny_records, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存出闪记录失败: {e}")
            return False
    
    def load_shiny_records(self):
        """从文件加载出闪记录"""
        if not os.path.exists(self.shiny_records_file):
            self.shiny_records = []
            return
        
        try:
            with open(self.shiny_records_file, 'r', encoding='utf-8') as f:
                self.shiny_records = json.load(f)
        except Exception as e:
            print(f"加载出闪记录失败: {e}")
            self.shiny_records = []
    
    def add_shiny_record(self, pokemon_name: str, count: int, is_shiny: bool):
        """添加一条出闪记录
        
        Args:
            pokemon_name: 精灵名称
            count: 本次出闪时的童话事件次数
            is_shiny: 是否出闪
        """
        import datetime
        record = {
            'id': f"sr_{len(self.shiny_records)+1}_{int(datetime.datetime.now().timestamp())}",
            'pokemon_name': pokemon_name,
            'count': count,
            'is_shiny': is_shiny,
            'timestamp': datetime.datetime.now().isoformat(),
            'date': datetime.datetime.now().strftime('%Y-%m-%d')
        }
        self.shiny_records.append(record)
        self.save_shiny_records()
        return record
    
    def get_shiny_records_by_date_range(self, start_date: str = None, end_date: str = None):
        """获取指定日期范围的出闪记录
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            筛选后的记录列表
        """
        filtered = []
        for record in self.shiny_records:
            record_date = record['date']
            if start_date and record_date < start_date:
                continue
            if end_date and record_date > end_date:
                continue
            filtered.append(record)
        return filtered
    
    def get_shiny_records_statistics(self, records: List[dict]):
        """统计出闪记录
        
        Returns:
            按精灵分组的统计数据，格式：
            {
                '精灵名': {
                    'total_attempts': 总尝试次数,
                    'shiny_count': 出闪次数,
                    'non_shiny_count': 未出闪次数,
                    'max_count': 最大次数,
                    'records': [记录列表]
                }
            }
        """
        stats = {}
        for record in records:
            name = record['pokemon_name']
            if name not in stats:
                stats[name] = {
                    'total_attempts': 0,
                    'shiny_count': 0,
                    'non_shiny_count': 0,
                    'max_count': 0,
                    'records': []
                }
            stats[name]['total_attempts'] += 1
            if record['is_shiny']:
                stats[name]['shiny_count'] += 1
            else:
                stats[name]['non_shiny_count'] += 1
            stats[name]['max_count'] = max(stats[name]['max_count'], record['count'])
            stats[name]['records'].append(record)
        return stats
    
    def clear_all_shiny_records(self):
        """清空所有出闪记录"""
        self.shiny_records = []
        self.save_shiny_records()
