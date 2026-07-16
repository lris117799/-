import json
import os

# 技能数据库路径
SKILL_DB_PATH = os.path.join(os.path.dirname(__file__), "skill_database.json")

class SkillDatabase:
    """技能数据库管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SkillDatabase, cls).__new__(cls)
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        """加载技能数据库"""
        self._skills = {}
        self._version = "0.0"
        
        if os.path.exists(SKILL_DB_PATH):
            try:
                with open(SKILL_DB_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._skills = data.get('skills', {})
                self._version = data.get('version', "0.0")
                print(f"✓ 技能数据库加载成功: {len(self._skills)} 个技能")
            except Exception as e:
                print(f"✗ 技能数据库加载失败: {e}")
    
    def get_skill(self, name):
        """获取技能信息"""
        return self._skills.get(name)
    
    def search_skills(self, keyword):
        """搜索技能（支持模糊匹配）"""
        keyword = keyword.lower()
        results = []
        for name, info in self._skills.items():
            if keyword in name.lower():
                results.append(info)
        return results
    
    def get_skills_by_type(self, skill_type):
        """按类型获取技能"""
        results = []
        for info in self._skills.values():
            if info.get('type') == skill_type:
                results.append(info)
        return results
    
    def get_all_skills(self):
        """获取所有技能"""
        return list(self._skills.values())
    
    def get_version(self):
        """获取数据库版本"""
        return self._version
    
    def get_total_count(self):
        """获取技能总数"""
        return len(self._skills)
    
    def update_skill_power(self, skill_name, power):
        """更新技能威力"""
        if skill_name in self._skills:
            self._skills[skill_name]['power'] = power
            self._save()
            return True
        return False
    
    def _save(self):
        """保存数据库"""
        data = {
            "version": self._version,
            "total_skills": len(self._skills),
            "skills": self._skills
        }
        with open(SKILL_DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# 全局实例
skill_db = SkillDatabase()

def get_skill_db():
    """获取技能数据库实例"""
    return skill_db

if __name__ == '__main__':
    # 测试
    db = get_skill_db()
    print(f"版本: {db.get_version()}")
    print(f"技能总数: {db.get_total_count()}")
    
    # 测试获取技能
    skill = db.get_skill("一拳")
    if skill:
        print(f"\n一拳: type={skill['type']}, power={skill['power']}, energy={skill['energy']}")
    
    # 测试搜索
    results = db.search_skills("雷")
    print(f"\n搜索'雷'找到 {len(results)} 个技能")
    for r in results[:3]:
        print(f"  {r['name']}: {r['type']}")