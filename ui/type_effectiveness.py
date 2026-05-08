"""
属性克制表界面
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QScrollArea, QFrame, QGridLayout
)
from PySide6.QtCore import Qt
import json


class TypeEffectivenessWidget(QWidget):
    """属性克制表界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.effectiveness_data = {}
        self.load_type_data()
        self.setup_ui()
    
    def load_type_data(self):
        """加载属性克制数据"""
        with open('D:/game/lkwg/属性克制.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析所有属性的克制关系
        all_types = ['草', '火', '水', '光', '地', '冰', '龙', '电', '毒', '虫', '武', '翼', '萌', '幽', '恶', '普', '幻', '机械']
        
        for attr in all_types:
            self.effectiveness_data[attr + '系'] = {
                'attack_2x': [],
                'attack_0.5x': [],
                'defense_2x': [],
                'defense_0.5x': []
            }
        
        # 按行解析
        current_attr = None
        section = None
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            # 跳过空行和分隔线
            if not line or line.startswith('===') or line.startswith('---') or line.startswith('•'):
                continue
            
            # 检测属性标题 【草系】
            if line.startswith('【') and line.endswith('】'):
                current_attr = line[1:-1]
                section = None  # 重置section
                continue
            
            # 检测章节（不continue，让数据行继续解析）
            if '攻击克制' in line and '2倍' in line:
                section = 'attack_2x'
            elif '攻击被抵抗' in line and '0.5倍' in line:
                section = 'attack_0.5x'
            elif '被克制' in line and '受2倍' in line:
                section = 'defense_2x'
            elif '抵抗' in line and '受0.5倍' in line:
                section = 'defense_0.5x'
            
            # 解析属性列表
            if current_attr and section and ('：' in line or ':' in line):
                parts = line.split('：') if '：' in line else line.split(':')
                if len(parts) >= 2:
                    text = parts[-1].strip()
                    if text and text != '无':
                        attrs = [a.strip() for a in text.split('、')]
                        self.effectiveness_data[current_attr][section] = attrs
    
    def setup_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("属性克制表")
        title_label.setStyleSheet("""
            color: #a78bfa;
            font-size: 28px;
            font-weight: bold;
        """)
        main_layout.addWidget(title_label)
                
        # 属性选择区域
        select_layout = QHBoxLayout()
        select_layout.setSpacing(15)
        
        select_layout.addWidget(QLabel("选择属性："))
        
        # 第一个属性选择
        self.type1_combo = QComboBox()
        self.type1_combo.addItem("请选择属性")
        all_types = sorted(self.effectiveness_data.keys())
        for t in all_types:
            self.type1_combo.addItem(t)
        self.type1_combo.setFixedWidth(160)
        self.type1_combo.setStyleSheet(self.combo_style())
        self.type1_combo.currentTextChanged.connect(self.update_display)
        select_layout.addWidget(self.type1_combo)
        
        select_layout.addWidget(QLabel("+"))
        
        # 第二个属性选择
        self.type2_combo = QComboBox()
        self.type2_combo.addItem("无（单属性）")
        for t in all_types:
            self.type2_combo.addItem(t)
        self.type2_combo.setFixedWidth(160)
        self.type2_combo.setStyleSheet(self.combo_style())
        self.type2_combo.currentTextChanged.connect(self.update_display)
        select_layout.addWidget(self.type2_combo)
        
        select_layout.addStretch()
        main_layout.addLayout(select_layout)
        
        # 结果显示区域（滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(139, 92, 246, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(139, 92, 246, 0.4);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(139, 92, 246, 0.6);
            }
        """)
        
        self.result_container = QWidget()
        self.result_layout = QVBoxLayout(self.result_container)
        self.result_layout.setContentsMargins(0, 20, 0, 20)
        self.result_layout.setSpacing(16)
        
        scroll.setWidget(self.result_container)
        main_layout.addWidget(scroll, 1)
        
        # 初始显示提示
        self.show_placeholder()
    
    def combo_style(self):
        return """
            QComboBox {
                background-color: rgba(22, 33, 62, 0.8);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 6px;
                padding: 8px 12px;
                color: white;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: white;
                selection-background-color: rgba(139, 92, 246, 0.4);
            }
        """
    
    def show_placeholder(self):
        """显示占位提示"""
        self.clear_result()
        
        placeholder = QLabel("请选择属性查看克制关系")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("""
            color: rgba(255, 255, 255, 0.4);
            font-size: 16px;
            padding: 60px;
        """)
        self.result_layout.addWidget(placeholder)
    
    def clear_result(self):
        """清空结果区域"""
        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def update_display(self):
        """更新显示"""
        type1 = self.type1_combo.currentText()
        type2 = self.type2_combo.currentText()
        
        if type1 == "请选择属性":
            self.show_placeholder()
            return
        
        self.clear_result()
        
        # 确定要显示的属性
        if type2 == "无（单属性）":
            selected_types = [type1]
            title_text = f"【{type1}】"
        else:
            selected_types = [type1, type2]
            title_text = f"【{type1} + {type2}】"
        
        # 标题
        title_label = QLabel(title_text)
        title_label.setStyleSheet("""
            color: #a78bfa;
            font-size: 20px;
            font-weight: bold;
            padding: 8px 0;
        """)
        self.result_layout.addWidget(title_label)
        
        # 如果是双属性，计算综合克制关系
        if len(selected_types) == 2:
            self.show_dual_type_effectiveness(selected_types)
        else:
            self.show_single_type_effectiveness(type1)
        
        self.result_layout.addStretch()
    
    def show_single_type_effectiveness(self, attr):
        """显示单属性克制关系"""
        data = self.effectiveness_data.get(attr, {})
        
        sections = [
            ("攻击克制（造成2倍伤害）", data.get('attack_2x', []), "#ef4444"),
            ("攻击被抵抗（造成0.5倍伤害）", data.get('attack_0.5x', []), "#f59e0b"),
            ("被克制（受到2倍伤害）", data.get('defense_2x', []), "#ef4444"),
            ("抵抗（受到0.5倍伤害）", data.get('defense_0.5x', []), "#10b981"),
        ]
        
        for title, types, color in sections:
            section_widget = self.create_section(title, types, color)
            self.result_layout.addWidget(section_widget)
    
    def show_dual_type_effectiveness(self, types):
        """显示双属性综合克制关系"""
        type1, type2 = types
        
        # 计算综合的攻击克制关系
        combined_attack_2x = set()
        combined_attack_half = set()
        combined_defense_2x = set()
        combined_defense_half = set()
        
        data1 = self.effectiveness_data.get(type1, {})
        data2 = self.effectiveness_data.get(type2, {})
        
        # 收集所有可能的攻击属性
        all_attackers = set()
        for key in ['defense_2x', 'defense_0.5x']:
            all_attackers.update(data1.get(key, []))
            all_attackers.update(data2.get(key, []))
        
        # 对每个攻击属性计算综合效果
        for attacker in all_attackers:
            # 计算对type1的效果
            mult1 = 1.0
            if attacker in data1.get('defense_2x', []):
                mult1 = 2.0
            elif attacker in data1.get('defense_0.5x', []):
                mult1 = 0.5
            
            # 计算对type2的效果
            mult2 = 1.0
            if attacker in data2.get('defense_2x', []):
                mult2 = 2.0
            elif attacker in data2.get('defense_0.5x', []):
                mult2 = 0.5
            
            # 综合效果
            final_mult = mult1 * mult2
            
            # 特殊规则：双属性都被克制是3倍而非4倍
            if mult1 == 2.0 and mult2 == 2.0:
                final_mult = 3.0
            
            if final_mult >= 2.0:
                combined_defense_2x.add(attacker)
            elif final_mult < 1.0:
                combined_defense_half.add(attacker)
        
        # 收集所有可能的防御属性
        all_defenders = set()
        for key in ['attack_2x', 'attack_0.5x']:
            all_defenders.update(data1.get(key, []))
            all_defenders.update(data2.get(key, []))
        
        # 对每个防御属性计算综合效果
        for defender in all_defenders:
            # 计算type1对defender的效果
            mult1 = 1.0
            if defender in data1.get('attack_2x', []):
                mult1 = 2.0
            elif defender in data1.get('attack_0.5x', []):
                mult1 = 0.5
            
            # 计算type2对defender的效果
            mult2 = 1.0
            if defender in data2.get('attack_2x', []):
                mult2 = 2.0
            elif defender in data2.get('attack_0.5x', []):
                mult2 = 0.5
            
            # 综合效果（取最大值，因为可以选择用哪个属性攻击）
            final_mult = max(mult1, mult2)
            
            if final_mult >= 2.0:
                combined_attack_2x.add(defender)
            elif final_mult < 1.0 and mult1 < 1.0 and mult2 < 1.0:
                # 只有两个属性都抵抗时才显示为抵抗
                combined_attack_half.add(defender)
        
        # 按单属性格式显示
        sections = [
            ("攻击克制（造成2倍伤害）", sorted(combined_attack_2x), "#ef4444"),
            ("攻击被抵抗（造成0.5倍伤害）", sorted(combined_attack_half), "#f59e0b"),
            ("被克制（受到2倍伤害）", sorted(combined_defense_2x), "#ef4444"),
            ("抵抗（受到0.5倍伤害）", sorted(combined_defense_half), "#10b981"),
        ]
        
        for title, types_list, color in sections:
            section_widget = self.create_section(title, types_list, color)
            self.result_layout.addWidget(section_widget)
    
    def create_section(self, title, types, color):
        """创建信息区块"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(6)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {color};
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(title_label)
        
        # 属性列表
        if types:
            types_text = "、".join(types)
            types_label = QLabel(types_text)
            types_label.setStyleSheet("""
                color: rgba(255, 255, 255, 0.9);
                font-size: 15px;
                padding: 2px 0;
                line-height: 1.5;
            """)
            types_label.setWordWrap(True)
            layout.addWidget(types_label)
        else:
            none_label = QLabel("无")
            none_label.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 14px;")
            layout.addWidget(none_label)
        
        return container
