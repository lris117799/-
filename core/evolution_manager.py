# core/evolution_manager.py
import os
import json

class EvolutionManager:
    def __init__(self):
        self.evolution_chains = {}  # {形态名: 基础精灵名}
        self.base_pokemon_names = set()
        self.custom_pokemons_file = os.path.join(os.path.dirname(__file__), "custom_pokemons.json")
        self._load_evolution_chains()
        self._load_custom_pokemons()  # 加载自定义精灵
    
    def _load_evolution_chains(self):
        """加载进化链配置"""
        names_file = os.path.join(os.path.dirname(__file__), "lkwg_names.txt")
        if not os.path.exists(names_file):
            return
        
        with open(names_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 解析进化链
                forms = [form.strip() for form in line.split('→')]
                if not forms:
                    continue
                
                # 第一个是基础精灵
                base_name = forms[0]
                self.base_pokemon_names.add(base_name)
                
                # 所有形态都映射到基础精灵
                for form in forms:
                    if form:
                        self.evolution_chains[form] = base_name
    
    def _load_custom_pokemons(self):
        """加载自定义精灵及其进化链"""
        if not os.path.exists(self.custom_pokemons_file):
            return
        
        try:
            with open(self.custom_pokemons_file, 'r', encoding='utf-8') as f:
                custom_pokemons = json.load(f)
            
            for pokemon in custom_pokemons:
                name = pokemon.get('name')
                if not name:
                    continue
                
                evolution_chain = pokemon.get('evolution_chain', [])
                if evolution_chain and len(evolution_chain) > 0:
                    # 有进化链：第一个是基础形态
                    base_name = evolution_chain[0]
                    self.base_pokemon_names.add(base_name)
                    for form in evolution_chain:
                        if form:
                            self.evolution_chains[form] = base_name
                else:
                    # 无进化链：单形态
                    self.base_pokemon_names.add(name)
                    self.evolution_chains[name] = name
        except Exception as e:
            print(f"加载自定义精灵失败: {e}")
    
    def add_custom_pokemon(self, name: str, evolution_chain: list = None):
        """
        添加自定义精灵到识别词库
        :param name: 精灵名称
        :param evolution_chain: 进化链列表，如['雪娃娃', '冰封怨灵', '雪灵']，None表示单形态
        """
        if evolution_chain and len(evolution_chain) > 0:
            # 有进化链
            base_name = evolution_chain[0]
            self.base_pokemon_names.add(base_name)
            for form in evolution_chain:
                if form:
                    self.evolution_chains[form] = base_name
        else:
            # 单形态
            self.base_pokemon_names.add(name)
            self.evolution_chains[name] = name
    
    def remove_custom_pokemon(self, name: str, evolution_chain: list = None):
        """
        从识别词库移除自定义精灵
        :param name: 精灵名称
        :param evolution_chain: 进化链列表（用于精确移除）
        """
        if evolution_chain and len(evolution_chain) > 0:
            # 有进化链：移除所有形态
            for form in evolution_chain:
                if form in self.evolution_chains:
                    del self.evolution_chains[form]
        else:
            # 单形态
            if name in self.evolution_chains:
                del self.evolution_chains[name]
        
        # 从基础精灵集合中移除
        if name in self.base_pokemon_names:
            self.base_pokemon_names.discard(name)
    
    def get_base_pokemon(self, recognized_name):
        """
        根据识别到的形态名获取基础精灵名
        :param recognized_name: OCR识别到的名称
        :return: 基础精灵名，如果未匹配返回None
        """
        return self.evolution_chains.get(recognized_name)
    
    def is_valid_pokemon(self, name):
        """检查名称是否是有效的精灵(含进化形态)"""
        return name in self.evolution_chains
