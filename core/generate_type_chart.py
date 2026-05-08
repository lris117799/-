"""
解析克制.txt并生成属性克制表
"""
import re

def parse_type_effectiveness():
    """解析克制关系文件"""
    with open('D:/game/lkwg/克制.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 定义所有属性
    all_types = ['草', '火', '水', '光', '地', '冰', '龙', '电', '毒', '虫', '武', '翼', '萌', '幽', '恶', '普', '幻', '机械']
    
    # 存储克制关系
    effectiveness = {}
    
    for attr in all_types:
        effectiveness[attr] = {
            'attack_2x': [],
            'attack_0.5x': [],
            'defense_2x': [],
            'defense_0.5x': []
        }
    
    current_attr = None
    section = None  # 'attack' or 'defense'
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 检测属性标题
        attr_match = re.match(r'Step\d+：(\w+)系', line)
        if attr_match:
            current_attr = attr_match.group(1)
            continue
        
        # 检测章节
        if '作为攻击方' in line:
            section = 'attack'
            continue
        elif '作为被攻击方' in line:
            section = 'defense'
            continue
        
        # 解析克制关系
        if current_attr and section:
            # 0.5倍伤害
            half_match = re.search(r'对(.+?)造成0\.5倍伤害', line)
            if half_match and section == 'attack':
                text = half_match.group(1)
                # 处理 "火/龙/毒/虫/翼/机械系" 格式
                attrs = [a.strip() + '系' for a in text.replace('系', '').split('/')]
                effectiveness[current_attr]['attack_0.5x'] = attrs
                continue
            
            half_match = re.search(r'受到(.+?)的0\.5倍伤害', line)
            if half_match and section == 'defense':
                text = half_match.group(1)
                attrs = [a.strip() + '系' for a in text.replace('系', '').split('/')]
                effectiveness[current_attr]['defense_0.5x'] = attrs
                continue
            
            # 2倍伤害
            double_match = re.search(r'对(.+?)造成2倍伤害', line)
            if double_match and section == 'attack':
                text = double_match.group(1)
                attrs = [a.strip() + '系' for a in text.replace('系', '').split('/')]
                effectiveness[current_attr]['attack_2x'] = attrs
                continue
            
            double_match = re.search(r'受到(.+?)的2倍伤害', line)
            if double_match and section == 'defense':
                text = double_match.group(1)
                attrs = [a.strip() + '系' for a in text.replace('系', '').split('/')]
                effectiveness[current_attr]['defense_2x'] = attrs
                continue
    
    return effectiveness, all_types


def calculate_damage_multiplier(attacker_attr, defender_attrs):
    """
    计算伤害倍率
    
    Args:
        attacker_attr: 攻击方的属性（单属性）
        defender_attrs: 防御方的属性列表（可以是1个或2个属性）
    
    Returns:
        float: 伤害倍率 (0.5, 1, 2, 3)
    """
    if isinstance(defender_attrs, str):
        defender_attrs = [defender_attrs]
    
    multiplier = 1.0
    weak_count = 0  # 被克制的属性数量
    resist_count = 0  # 抵抗的属性数量
    
    for defender_attr in defender_attrs:
        # 检查攻击属性是否克制防御属性
        if attacker_attr in effectiveness.get(defender_attr, {}).get('defense_2x', []):
            weak_count += 1
        elif attacker_attr in effectiveness.get(defender_attr, {}).get('defense_0.5x', []):
            resist_count += 1
    
    # 根据规则计算最终倍率
    if weak_count == 0 and resist_count == 0:
        return 1.0
    elif weak_count == 1 and resist_count == 0:
        return 2.0
    elif weak_count == 2 and resist_count == 0:
        return 3.0  # 双属性都被克制，3倍而非4倍
    elif weak_count == 0 and resist_count == 1:
        return 0.5
    elif weak_count == 0 and resist_count == 2:
        return 0.5  # 双属性都抵抗，仍为0.5倍
    elif weak_count == 1 and resist_count == 1:
        return 1.0  # 一克一抗，抵消
    
    return 1.0


def generate_type_chart():
    """生成属性克制表"""
    effectiveness, all_types = parse_type_effectiveness()
    
    lines = []
    lines.append("=" * 80)
    lines.append("洛克王国世界 - 属性克制表")
    lines.append("=" * 80)
    lines.append("")
    lines.append("说明：")
    lines.append("  • 单属性被克制 = 2倍伤害")
    lines.append("  • 双属性都被同一属性克制 = 3倍伤害（不是4倍）")
    lines.append("  • 单属性抵抗 = 0.5倍伤害")
    lines.append("  • 双属性都抵抗 = 0.5倍伤害")
    lines.append("  • 一克一抗 = 1倍伤害（相互抵消）")
    lines.append("")
    lines.append("=" * 80)
    lines.append("")
    
    # 为每个属性生成详细信息
    for attr in all_types:
        lines.append(f"【{attr}系】")
        lines.append("-" * 40)
        
        info = effectiveness[attr]
        
        # 攻击克制
        if info['attack_2x']:
            lines.append(f"  攻击克制（2倍）：{'、'.join(info['attack_2x'])}")
        else:
            lines.append(f"  攻击克制（2倍）：无")
        
        if info['attack_0.5x']:
            lines.append(f"  攻击被抵抗（0.5倍）：{'、'.join(info['attack_0.5x'])}")
        else:
            lines.append(f"  攻击被抵抗（0.5倍）：无")
        
        lines.append("")
        
        # 被攻击克制
        if info['defense_2x']:
            lines.append(f"  被克制（受2倍伤害）：{'、'.join(info['defense_2x'])}")
        else:
            lines.append(f"  被克制（受2倍伤害）：无")
        
        if info['defense_0.5x']:
            lines.append(f"  抵抗（受0.5倍伤害）：{'、'.join(info['defense_0.5x'])}")
        else:
            lines.append(f"  抵抗（受0.5倍伤害）：无")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("")
    
    # 生成双属性示例
    lines.append("双属性克制示例：")
    lines.append("-" * 40)
    lines.append("  • 火+机械 vs 水系：火系抵抗(0.5x) + 机械被克制(2x) = 1倍")
    lines.append("  • 草+地面 vs 冰系：草被克制(2x) + 地被克制(2x) = 3倍")
    lines.append("  • 火+钢 vs 水系：火被克制(2x) + 钢被克制(2x) = 3倍")
    lines.append("  • 火+钢 vs 火系：火抵抗(0.5x) + 钢抵抗(0.5x) = 0.5倍")
    lines.append("")
    lines.append("=" * 80)
    
    return '\n'.join(lines)


if __name__ == "__main__":
    print("解析克制关系...")
    effectiveness, all_types = parse_type_effectiveness()
    
    print(f"成功解析 {len(all_types)} 个属性的克制关系")
    
    print("\n生成属性克制表...")
    chart_content = generate_type_chart()
    
    output_file = 'D:/game/lkwg/属性克制.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(chart_content)
    
    print(f"✓ 属性克制表已保存到: {output_file}")
    print(f"\n预览前100行:")
    print('\n'.join(chart_content.split('\n')[:100]))
