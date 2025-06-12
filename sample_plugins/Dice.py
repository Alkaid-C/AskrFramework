"""
Spring 骰娘插件 - 基于 Askr Framework
为COC TRPG跑团提供完整的角色卡管理和掷骰功能
"""

import sqlite3
import json
import random
import hashlib
import datetime
import os
import re
from typing import Tuple, Dict, Any, Optional, List

# ================================
# 配置和常量
# ================================

# MANIFEST声明
MANIFEST = {
    "INITIALIZER": "init_database",
    "MESSAGE_GROUP_BOT": "handle_group_command",
    "MESSAGE_PRIVATE": "handle_private_command"
}

# 配置常量
CONFIG = {
    "database_path": "plugins/spring/spring.db",
    "help_file": "plugins/help.json", 
    "madness_file": "plugins/madness.json",
    "max_command_length": 30,
    "max_name_length": 30
}

# 掷骰系统参数限制
LIMITS = {
    'n': 10,    # 骰子数量最大值
    'b': 10,    # 奖励骰数最大值  
    'p': 10,    # 惩罚骰数最大值
    'm': 1000   # 骰子面数最大值
}

# ================================
# 掷骰系统核心函数
# ================================

def skill_check_result(skill_level: int, roll_result: int, roomrule: int = 0) -> str:
    """
    技能检定辅助函数，返回成功/失败/大成功/大失败的判定
    
    Args:
        skill_level: 技能等级 (0-100)
        roll_result: 掷骰结果 (1-100) 
        roomrule: 房规 (0-6)
    
    Returns:
        判定结果字符串
    """
    # 提取个位数和十位数用于房规6
    ones_digit = roll_result % 10
    tens_digit = (roll_result // 10) % 10
    
    # 房规判定逻辑
    if roomrule == 0:  # 规则书标准
        if roll_result == 1:
            return "大成功"
        elif skill_level < 50 and 96 <= roll_result <= 100:
            return "大失败"
        elif skill_level >= 50 and roll_result == 100:
            return "大失败"
        elif roll_result <= skill_level:
            return "成功"
        else:
            return "失败"
    
    elif roomrule == 1:  # 成功率影响大成功判定
        # 大成功判定
        if skill_level < 50 and roll_result == 1:
            is_critical_success = True
        elif skill_level >= 50 and 1 <= roll_result <= 5:
            is_critical_success = True
        else:
            is_critical_success = False
        
        # 大失败判定
        if skill_level < 50 and 96 <= roll_result <= 100:
            is_critical_failure = True
        elif skill_level >= 50 and roll_result == 100:
            is_critical_failure = True
        else:
            is_critical_failure = False
        
        if is_critical_success:
            return "大成功"
        elif is_critical_failure:
            return "大失败"
        elif roll_result <= skill_level:
            return "成功"
        else:
            return "失败"
    
    elif roomrule == 2:  # 1-5大成功，96-100大失败条件判定
        if 1 <= roll_result <= 5 and roll_result <= skill_level:
            return "大成功"
        elif (roll_result == 100) or (96 <= roll_result <= 99 and roll_result > skill_level):
            return "大失败"
        elif roll_result <= skill_level:
            return "成功"
        else:
            return "失败"
    
    elif roomrule == 3:  # 固定1-5大成功，96-100大失败
        if 1 <= roll_result <= 5:
            return "大成功"
        elif 96 <= roll_result <= 100:
            return "大失败"
        elif roll_result <= skill_level:
            return "成功"
        else:
            return "失败"
    
    elif roomrule == 4:  # 大成功/大失败与成功率相关
        critical_success_threshold = max(1, skill_level // 10)
        
        if 1 <= roll_result <= 5 and roll_result <= critical_success_threshold:
            return "大成功"
        elif skill_level < 50 and roll_result >= 96 + (skill_level // 10):
            return "大失败"
        elif skill_level >= 50 and roll_result == 100:
            return "大失败"
        elif roll_result <= skill_level:
            return "成功"
        else:
            return "失败"
    
    elif roomrule == 5:  # 1-2大成功，高概率大失败
        critical_success_threshold = max(1, skill_level // 5)
        
        if 1 <= roll_result <= 2 and roll_result < critical_success_threshold:
            return "大成功"
        elif skill_level < 50 and 96 <= roll_result <= 100:
            return "大失败"
        elif skill_level >= 50 and 99 <= roll_result <= 100:
            return "大失败"
        elif roll_result <= skill_level:
            return "成功"
        else:
            return "失败"
    
    elif roomrule == 6:  # 对子判定法
        if ones_digit == tens_digit and roll_result <= skill_level:
            return "大成功"
        elif ones_digit == tens_digit and roll_result > skill_level:
            return "大失败"
        elif roll_result <= skill_level:
            return "成功"
        else:
            return "失败"
    
    else:  # 未知房规，使用规则书标准
        return skill_check_result(skill_level, roll_result, 0)

def get_d100_tens_ones(roll: int, is_base_dice: bool) -> Tuple[int, int]:
    """
    获取d100骰子的十位数和个位数
    is_base_dice: True为基础骰，False为奖励/惩罚骰
    """
    if roll == 100:
        if is_base_dice:
            return 10, 0  # 基础骰100的十位为10
        else:
            return 0, 0   # 奖励/惩罚骰100的十位为0
    else:
        return roll // 10, roll % 10

def roll_bonus_penalty_d100(bonus_dice: int, penalty_dice: int) -> str:
    """执行奖励/惩罚骰的d100投掷"""
    original_roll = random.randint(1, 100)
    original_tens, original_ones = get_d100_tens_ones(original_roll, True)
    
    if bonus_dice > 0:
        bonus_rolls = [random.randint(1, 100) for _ in range(bonus_dice)]
        bonus_tens_list = [get_d100_tens_ones(roll, False)[0] for roll in bonus_rolls]
        best_tens = min([original_tens] + bonus_tens_list)
        final_result = best_tens * 10 + original_ones
        if final_result == 0:
            final_result = 100
        return f"1d100({bonus_dice}个奖励骰): 原始{original_roll} 奖励骰{bonus_rolls} 结果{final_result}"
    
    elif penalty_dice > 0:
        penalty_rolls = [random.randint(1, 100) for _ in range(penalty_dice)]
        penalty_tens_list = [get_d100_tens_ones(roll, False)[0] for roll in penalty_rolls]
        worst_tens = max([original_tens] + penalty_tens_list)
        final_result = worst_tens * 10 + original_ones
        if final_result == 0:
            final_result = 100
        return f"1d100({penalty_dice}个惩罚骰): 原始{original_roll} 惩罚骰{penalty_rolls} 结果{final_result}"

def roll_skill_check_d100(skill_level: int, bonus_dice: int, penalty_dice: int, roomrule: int = 0) -> str:
    """执行技能检定的d100投掷"""
    original_roll = random.randint(1, 100)
    original_tens, original_ones = get_d100_tens_ones(original_roll, True)
    
    if bonus_dice > 0:
        bonus_rolls = [random.randint(1, 100) for _ in range(bonus_dice)]
        bonus_tens_list = [get_d100_tens_ones(roll, False)[0] for roll in bonus_rolls]
        best_tens = min([original_tens] + bonus_tens_list)
        final_result = best_tens * 10 + original_ones
        if final_result == 0:
            final_result = 100
        check_result = skill_check_result(skill_level, final_result, roomrule)
        return f"技能检定({skill_level}) {bonus_dice}个奖励骰: 原始{original_roll} 奖励骰{bonus_rolls} 结果{final_result} {check_result}"
    
    elif penalty_dice > 0:
        penalty_rolls = [random.randint(1, 100) for _ in range(penalty_dice)]
        penalty_tens_list = [get_d100_tens_ones(roll, False)[0] for roll in penalty_rolls]
        worst_tens = max([original_tens] + penalty_tens_list)
        final_result = worst_tens * 10 + original_ones
        if final_result == 0:
            final_result = 100
        check_result = skill_check_result(skill_level, final_result, roomrule)
        return f"技能检定({skill_level}) {penalty_dice}个惩罚骰: 原始{original_roll} 惩罚骰{penalty_rolls} 结果{final_result} {check_result}"
    
    else:
        roll_result = random.randint(1, 100)
        check_result = skill_check_result(skill_level, roll_result, roomrule)
        return f"技能检定({skill_level}): {roll_result} {check_result}"

def evaluate_dice_expression(expression: str, default_dice_sides: int) -> str:
    """计算掷骰表达式"""
    original_expr = expression
    
    # 骰子表达式正则：支持骰子面数的括号表达式，但骰子数量必须是纯数字
    dice_pattern = r'(\d*)d([^k\s+\-*/]*(?:\([^)]*\))?[^k\s+\-*/]*)(?:k(\d+))?'
    dice_results = []
    
    def replace_dice(match):
        dice_count_str = match.group(1)
        dice_sides_str = match.group(2)
        keep_highest_str = match.group(3)
        
        # 处理骰子数量 - 必须是纯数字，不支持表达式
        if dice_count_str:
            if not dice_count_str.isdigit():
                raise ValueError("骰子数量不支持表达式运算")
            dice_count = int(dice_count_str)
        else:
            dice_count = 1
        
        # 处理骰子面数 - 支持表达式
        if dice_sides_str.strip():
            try:
                # 如果是纯数字，直接转换
                if dice_sides_str.isdigit():
                    dice_sides = int(dice_sides_str)
                else:
                    # 包含表达式，先计算
                    dice_sides = eval(dice_sides_str)
                    if not isinstance(dice_sides, (int, float)):
                        raise ValueError("骰子面数必须是数字")
                    dice_sides = int(dice_sides)
            except:
                raise ValueError("无效的骰子面数表达式")
        else:
            dice_sides = default_dice_sides
        
        # 处理保留最大值
        keep_highest = None
        if keep_highest_str:
            if not keep_highest_str.isdigit():
                raise ValueError("保留数量必须是数字")
            keep_highest = int(keep_highest_str)
        
        # 参数限制检查
        if dice_count > LIMITS['n']:
            raise ValueError(f"骰子数量不能超过{LIMITS['n']}")
        if dice_sides > LIMITS['m']:
            raise ValueError(f"骰子面数不能超过{LIMITS['m']}")
        if dice_count <= 0 or dice_sides <= 0:
            raise ValueError("骰子数量和面数必须大于0")
        
        rolls = [random.randint(1, dice_sides) for _ in range(dice_count)]
        
        if keep_highest:
            if keep_highest > dice_count:
                raise ValueError("保留数量不能大于骰子数量")
            if keep_highest <= 0:
                raise ValueError("保留数量必须大于0")
            kept_rolls = sorted(rolls, reverse=True)[:keep_highest]
            result = sum(kept_rolls)
            dice_results.append(f"{dice_count}d{dice_sides}k{keep_highest}: {rolls} 保留{kept_rolls}")
        else:
            result = sum(rolls)
            dice_results.append(f"{dice_count}d{dice_sides}: {rolls}")
        
        return str(result)
    
    # 首先检查是否有骰子数量表达式（这是不允许的）
    invalid_count_pattern = r'\([^)]+\)d'
    if re.search(invalid_count_pattern, expression):
        raise ValueError("骰子数量不支持表达式运算")
    
    # 替换所有骰子表达式为结果
    processed_expr = re.sub(dice_pattern, replace_dice, expression)
    
    # 计算最终结果
    try:
        final_result = eval(processed_expr)
        if dice_results:
            details = " | ".join(dice_results)
            return f"{original_expr}: {details} = {final_result}"
        else:
            return f"{original_expr}: {final_result}"
    except Exception as e:
        raise ValueError("无效的数学表达式")

def handle_skill_check(skill_level_expr: str, bonus_dice: int, penalty_dice: int, default_dice_sides: int, roomrule: int = 0) -> str:
    """处理技能检定"""
    if not skill_level_expr.strip():
        return "错误：技能检定需要指定技能等级"
    
    # 使用空格分界，只取第一部分作为技能等级，忽略后续杂音
    parts = skill_level_expr.strip().split()
    if not parts or not parts[0]:
        return "错误：技能检定需要指定技能等级"
    
    actual_skill_expr = parts[0]  # 只使用第一部分
    
    # 计算技能等级（支持四则运算）
    try:
        skill_level = eval(actual_skill_expr)
        if not isinstance(skill_level, (int, float)):
            return "错误：技能等级必须是数字"
        skill_level = int(skill_level)
        
        if skill_level < 0 or skill_level > 100:
            return "错误：技能等级必须在0-100之间"
    except:
        return "错误：无效的技能等级表达式"
    
    return roll_skill_check_d100(skill_level, bonus_dice, penalty_dice, roomrule)

def handle_normal_roll(expression: str, bonus_dice: int, penalty_dice: int, default_dice_sides: int) -> str:
    """处理普通掷骰"""
    if bonus_dice > 0 or penalty_dice > 0:
        # 奖励/惩罚骰只能用于d100
        if expression and 'd' in expression:
            dice_pattern = r'(\d*)d(\d*)'
            matches = re.findall(dice_pattern, expression)
            for match in matches:
                dice_sides = int(match[1]) if match[1] else default_dice_sides
                if dice_sides != 100:
                    return "错误：奖励骰和惩罚骰只能用于d100"
        
        return roll_bonus_penalty_d100(bonus_dice, penalty_dice)
    
    # 处理普通表达式
    if not expression:
        result = random.randint(1, default_dice_sides)
        return f"1d{default_dice_sides}: {result}"
    
    try:
        return evaluate_dice_expression(expression, default_dice_sides)
    except Exception as e:
        return f"错误：{str(e)}"

def parse_parameters(content: str) -> Tuple[bool, bool, int, int, str]:
    """
    解析参数
    返回: (is_hidden, is_skill_check, bonus_dice, penalty_dice, remaining_content)
    """
    is_hidden = False
    is_skill_check = False
    bonus_dice = 0
    penalty_dice = 0
    param_chars_seen = set()
    
    # 识别所有参数字符和它们的位置
    param_positions = []
    i = 0
    
    while i < len(content):
        char = content[i]
        if char in 'hacbp':
            if char in param_chars_seen:
                raise ValueError("重复参数")
            param_chars_seen.add(char)
            
            if char == 'h':
                is_hidden = True
                param_positions.append(('h', i, None, i + 1))
                i += 1
            elif char in 'ac':
                is_skill_check = True
                param_positions.append(('a', i, None, i + 1))
                i += 1
            elif char in 'bp':
                # 查找紧跟的数字
                j = i + 1
                num_str = ""
                while j < len(content) and content[j].isdigit():
                    num_str += content[j]
                    j += 1
                
                immediate_num = int(num_str) if num_str else None
                param_positions.append((char, i, immediate_num, j))
                i = j
            else:
                i += 1
        else:
            break
    
    # 检查参数冲突
    has_b = any(p[0] == 'b' for p in param_positions)
    has_p = any(p[0] == 'p' for p in param_positions)
    if has_b and has_p:
        raise ValueError("奖励骰和惩罚骰不能同时使用")
    
    # 找到参数区域结束位置
    param_end = max((p[3] for p in param_positions), default=0)
    remaining_content = content[param_end:].strip()
    
    # 分配参数值
    if is_skill_check:
        # 技能检定模式的参数分配
        b_param = next((p for p in param_positions if p[0] == 'b'), None)
        p_param = next((p for p in param_positions if p[0] == 'p'), None)
        skill_level_expr = remaining_content
        
        if b_param or p_param:
            bp_param = b_param or p_param
            param_type = bp_param[0]
            immediate_value = bp_param[2]
            
            if immediate_value is not None:
                # b/p有紧跟数字
                if param_type == 'b':
                    bonus_dice = immediate_value
                else:
                    penalty_dice = immediate_value
                    
                # 从remaining_content中移除这个数字
                pattern = r'\b' + str(immediate_value) + r'\b'
                if re.search(pattern, skill_level_expr):
                    skill_level_expr = re.sub(pattern, '', skill_level_expr, count=1).strip()
            else:
                # b/p没有紧跟数字，使用默认值1
                if param_type == 'b':
                    bonus_dice = 1
                else:
                    penalty_dice = 1
        
        remaining_content = skill_level_expr
    else:
        # 普通掷骰模式
        b_param = next((p for p in param_positions if p[0] == 'b'), None)
        p_param = next((p for p in param_positions if p[0] == 'p'), None)
        
        if b_param:
            bonus_dice = b_param[2] if b_param[2] is not None else 1
        if p_param:
            penalty_dice = p_param[2] if p_param[2] is not None else 1
    
    # 验证参数限制
    if bonus_dice > LIMITS['b']:
        raise ValueError(f"奖励骰数量不能超过{LIMITS['b']}")
    if penalty_dice > LIMITS['p']:
        raise ValueError(f"惩罚骰数量不能超过{LIMITS['p']}")
    
    return is_hidden, is_skill_check, bonus_dice, penalty_dice, remaining_content

def roll_dice(command: str, default_dice_sides: int, seed: int, roomrule: int = 0) -> Tuple[bool, str]:
    """
    掷骰函数主实现
    返回: (is_hidden, result_string)
    """
    random.seed(seed)
    
    # 移除开头的.r
    if not command.startswith('.r'):
        return False, "错误：无效指令格式"
    
    content = command[2:]  # 移除.r
    
    try:
        is_hidden, is_skill_check, bonus_dice, penalty_dice, remaining_content = parse_parameters(content)
        
        if is_skill_check:
            result = handle_skill_check(remaining_content, bonus_dice, penalty_dice, default_dice_sides, roomrule)
        else:
            result = handle_normal_roll(remaining_content, bonus_dice, penalty_dice, default_dice_sides)
            
        return is_hidden, result
            
    except ValueError as e:
        return False, f"错误：{str(e)}"
    except Exception as e:
        return False, f"错误：{str(e)}"

# ================================
# 数据库操作函数
# ================================

def get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect(CONFIG["database_path"])

def ensure_user_exists(user_id: str):
    """确保用户记录存在"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def ensure_group_exists(group_id: str):
    """确保群组记录存在"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO groups (group_id) VALUES (?)", (group_id,))
    conn.commit()
    conn.close()

def ensure_group_user_exists(user_id: str, group_id: str):
    """确保群组用户记录存在"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO group_users (user_id, group_id) VALUES (?, ?)", 
                   (user_id, group_id))
    conn.commit()
    conn.close()

def is_bot_enabled(group_id: str) -> bool:
    """检查机器人是否在群内开启"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT bot_on FROM groups WHERE group_id = ?", (group_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0]

def get_user_nickname(user_id: str, group_id: str = "", rawEvent=None) -> str:
    """获取用户昵称，按优先级：群组昵称 > 全局昵称 > sender nickname"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    nickname = None
    
    # 群组昵称
    if group_id:
        cursor.execute("SELECT nickname FROM group_users WHERE user_id = ? AND group_id = ?", 
                       (user_id, group_id))
        result = cursor.fetchone()
        if result and result[0]:
            nickname = result[0]
    
    # 全局昵称
    if not nickname:
        cursor.execute("SELECT nickname FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result and result[0]:
            nickname = result[0]
    
    # sender nickname
    if not nickname and rawEvent:
        nickname = rawEvent.get("sender", {}).get("nickname", "")
    
    conn.close()
    return nickname or f"用户{user_id}"

def get_current_character(user_id: str, group_id: str, is_group: bool) -> Optional[tuple]:
    """获取用户当前默认角色卡"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取角色卡ID
    char_id = None
    if is_group:
        cursor.execute("SELECT char_id FROM group_users WHERE user_id = ? AND group_id = ?",
                       (user_id, group_id))
        result = cursor.fetchone()
        if result:
            char_id = result[0]
    
    if not char_id:
        cursor.execute("SELECT char_id FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            char_id = result[0]
    
    if not char_id:
        conn.close()
        return None
    
    # 获取角色卡详情
    cursor.execute("SELECT * FROM characters WHERE id = ?", (char_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result

def get_next_shown_id(user_id: str) -> int:
    """获取用户下一个可用的shown_id"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(shown_id) FROM characters WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        return result[0] + 1
    else:
        return 1

def find_character(user_id: str, identifier: str) -> Optional[tuple]:
    """根据名称或编号查找角色卡"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 尝试按编号查找
    try:
        shown_id = int(identifier)
        cursor.execute("SELECT * FROM characters WHERE user_id = ? AND shown_id = ?",
                       (user_id, shown_id))
        result = cursor.fetchone()
        if result:
            conn.close()
            return result
    except ValueError:
        pass
    
    # 按名称查找
    cursor.execute("SELECT * FROM characters WHERE user_id = ? AND name = ?",
                   (user_id, identifier))
    result = cursor.fetchone()
    conn.close()
    
    return result

# ================================
# 初始化和主要处理函数
# ================================

def init_database(botContext):
    """插件初始化函数"""
    try:
        # 创建数据目录
        os.makedirs("spring", exist_ok=True)
        
        # 连接数据库
        conn = sqlite3.connect(CONFIG["database_path"])
        cursor = conn.cursor()
        
        # 创建表结构
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            nickname TEXT,
            char_id INTEGER,
            FOREIGN KEY (char_id) REFERENCES characters(id)
        );
        
        CREATE TABLE IF NOT EXISTS groups (
            group_id TEXT PRIMARY KEY,
            default_dice INTEGER DEFAULT 100,
            roomrule INTEGER DEFAULT 0,
            bot_on BOOLEAN DEFAULT 1
        );
        
        CREATE TABLE IF NOT EXISTS group_users (
            user_id TEXT,
            group_id TEXT,
            nickname TEXT,
            char_id INTEGER,
            PRIMARY KEY (user_id, group_id),
            FOREIGN KEY (char_id) REFERENCES characters(id)
        );
        
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id TEXT NOT NULL,
            shown_id INTEGER NOT NULL,
            rule TEXT DEFAULT 'coc7',
            check_data TEXT DEFAULT '{}',
            flavor_data TEXT DEFAULT '{}',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """)
        
        conn.commit()
        conn.close()
        
        # 检查配置文件
        if not os.path.exists(CONFIG["help_file"]):
            raise Exception("help.json 文件不存在")
        if not os.path.exists(CONFIG["madness_file"]):
            raise Exception("madness.json 文件不存在")
            
        return None
        
    except Exception as e:
        raise Exception(f"Spring骰娘初始化失败: {str(e)}")

def handle_group_command(simpleEvent, rawEvent, botContext):
    """处理群聊指令"""
    return handle_command(simpleEvent, rawEvent, botContext, is_group=True)

def handle_private_command(simpleEvent, rawEvent, botContext):
    """处理私聊指令"""
    return handle_command(simpleEvent, rawEvent, botContext, is_group=False)

def handle_command(simpleEvent, rawEvent, botContext, is_group: bool):
    """统一指令处理函数"""
    try:
        message = simpleEvent["text_message"].strip()
        user_id = str(simpleEvent["user_id"])
        group_id = str(simpleEvent.get("group_id", "")) if is_group else ""
        
        # 检查指令长度
        if len(message) > CONFIG["max_command_length"]:
            return "指令长度超过限制（30字符）"
        
        # 确保用户和群组数据存在
        ensure_user_exists(user_id)
        if is_group:
            ensure_group_exists(group_id)
            ensure_group_user_exists(user_id, group_id)
            
            # 检查机器人开关状态
            if not is_bot_enabled(group_id):
                return None
        
        # 解析指令
        if message.startswith(".help"):
            return cmd_help(message)
        elif message.startswith(".bot"):
            return cmd_bot(message, group_id, is_group)
        elif message.startswith(".dismiss"):
            return cmd_dismiss(group_id, is_group)
        elif message.startswith(".r"):
            return cmd_roll(message, user_id, group_id, is_group, rawEvent)
        elif message.startswith(".set"):
            return cmd_set(message, group_id, is_group)
        elif message.startswith(".nn"):
            return cmd_nickname(message, user_id, group_id, is_group)
        elif message.startswith(".coc"):
            return cmd_coc(message)
        elif message.startswith(".pc"):
            return cmd_pc(message, user_id, group_id, is_group)
        elif message.startswith(".st"):
            return cmd_st(message, user_id, group_id, is_group)
        elif message.startswith(".setcoc"):
            return cmd_setcoc(message, group_id, is_group)
        elif message.startswith(".sc"):
            return cmd_sc(message, user_id, group_id, is_group)
        elif message.startswith(".ti") or message.startswith(".li"):
            return cmd_madness()
        elif message.startswith(".en"):
            return cmd_enhance(message, user_id, group_id, is_group)
        else:
            return None
            
    except Exception as e:
        return f"处理指令时发生错误: {str(e)}"

# ================================
# 指令实现函数
# ================================

def cmd_help(message: str) -> str:
    """帮助指令"""
    try:
        with open(CONFIG["help_file"], 'r', encoding='utf-8') as f:
            help_data = json.load(f)
        
        parts = message.split()
        if len(parts) == 1:
            # 显示所有指令
            result = "📖 Spring骰娘指令帮助\n"
            for cmd, desc in help_data.items():
                result += f".{cmd} - {desc.split('\\n')[0]}\n"
            return result.strip()
        else:
            # 显示特定指令
            cmd_name = parts[1]
            if cmd_name in help_data:
                return f"📖 .{cmd_name} 指令帮助\n{help_data[cmd_name]}"
            else:
                return f"未找到指令 .{cmd_name} 的帮助信息"
                
    except Exception:
        return "读取帮助文件失败"

def cmd_bot(message: str, group_id: str, is_group: bool) -> str:
    """机器人开关指令"""
    if not is_group:
        return "该指令仅限群聊使用"
    
    parts = message.split()
    if len(parts) != 2 or parts[1] not in ["on", "off"]:
        return "参数错误！正确格式：.bot [on/off]"
    
    new_status = parts[1] == "on"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE groups SET bot_on = ? WHERE group_id = ?", (new_status, group_id))
    conn.commit()
    conn.close()
    
    return f"机器人已{'开启' if new_status else '关闭'}"

def cmd_dismiss(group_id: str, is_group: bool):
    """退群指令"""
    if not is_group:
        return "该指令仅限群聊使用"
    
    # 清理数据库记录
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM groups WHERE group_id = ?", (group_id,))
    cursor.execute("DELETE FROM group_users WHERE group_id = ?", (group_id,))
    conn.commit()
    conn.close()
    
    # 返回退群操作
    return [
        "Spring骰娘即将退出本群，感谢使用！",
        {
            "action": "set_group_leave",
            "data": {
                "group_id": int(group_id)
            }
        }
    ]

def cmd_roll(message: str, user_id: str, group_id: str, is_group: bool, rawEvent) -> str:
    """掷骰指令"""
    # 获取默认骰子面数和房规
    default_dice = 100
    roomrule = 0
    
    if is_group:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT default_dice, roomrule FROM groups WHERE group_id = ?", (group_id,))
        result = cursor.fetchone()
        if result:
            default_dice = result[0]
            roomrule = result[1] if result[1] is not None else 0
        conn.close()
    
    # 获取用户角色卡进行技能替换
    command = message[2:].strip()  # 去掉.r
    reason = ""
    
    # 获取当前角色卡
    char_data = get_current_character(user_id, group_id, is_group)
    if char_data:
        check_data = json.loads(char_data[5])  # check_data字段
        
        # 技能名替换
        for skill_name, skill_value in check_data.items():
            if isinstance(skill_value, (int, float)) and skill_name in command:
                command = command.replace(skill_name, str(int(skill_value)))
                if not reason:
                    reason = skill_name
    
    # 生成随机种子
    system_random = random.SystemRandom().randint(1, 1000000)
    seed_string = f"{system_random}{user_id}"
    seed = int(hashlib.md5(seed_string.encode()).hexdigest(), 16) % (2**32)
    
    # 调用掷骰函数
    is_secret, result = roll_dice(f".r{command}", default_dice, seed, roomrule)
    
    # 获取昵称
    nickname = get_user_nickname(user_id, group_id, rawEvent)
    
    # 构造返回消息
    if reason:
        final_result = f"因为{reason}，{nickname}投掷出了{result}"
    else:
        final_result = f"{nickname}投掷出了{result}"
    
    # 根据是否暗骰返回
    if is_secret and is_group:
        return [
            "暗骰结果已私信发送",
            {
                "action": "send_private_msg",
                "data": {
                    "user_id": int(user_id),
                    "message": [{"type": "text", "data": {"text": final_result}}]
                }
            }
        ]
    else:
        return final_result

def cmd_set(message: str, group_id: str, is_group: bool) -> str:
    """设置默认骰指令"""
    if not is_group:
        return "该指令仅限群聊使用"
    
    parts = message.split()
    if len(parts) != 2:
        return "参数错误！正确格式：.set [面数]"
    
    try:
        dice_sides = int(parts[1])
        if dice_sides < 2:
            return "骰子面数不能小于2"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE groups SET default_dice = ? WHERE group_id = ?", 
                       (dice_sides, group_id))
        conn.commit()
        conn.close()
        
        return f"默认骰子面数已设置为{dice_sides}"
        
    except ValueError:
        return "参数错误！面数必须是数字"

def cmd_nickname(message: str, user_id: str, group_id: str, is_group: bool) -> str:
    """设置昵称指令"""
    # 支持.nn名字 和 .nn 名字 两种格式
    if message.startswith(".nn "):
        nickname = message[4:].strip()
    else:
        nickname = message[3:].strip()
    
    if not nickname:
        return "参数错误！昵称不能为空"
    
    if len(nickname) > CONFIG["max_name_length"]:
        return f"昵称长度不能超过{CONFIG['max_name_length']}字符"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if is_group:
        cursor.execute("UPDATE group_users SET nickname = ? WHERE user_id = ? AND group_id = ?",
                       (nickname, user_id, group_id))
    else:
        cursor.execute("UPDATE users SET nickname = ? WHERE user_id = ?", (nickname, user_id))
    
    conn.commit()
    conn.close()
    
    return f"昵称已设置为：{nickname}"

def cmd_coc(message: str) -> str:
    """COC角色生成指令"""
    parts = message.split()
    count = 1
    
    if len(parts) > 1:
        try:
            count = int(parts[1])
            if count < 1 or count > 10:
                return "生成数量必须在1-10之间"
        except ValueError:
            return "参数错误！数量必须是数字"
    
    results = []
    for i in range(count):
        # 基础属性生成
        stats = {}
        stats["力量"] = sum(random.randint(1, 6) for _ in range(3)) * 5
        stats["体质"] = sum(random.randint(1, 6) for _ in range(3)) * 5
        stats["体型"] = (sum(random.randint(1, 6) for _ in range(2)) + 6) * 5
        stats["敏捷"] = sum(random.randint(1, 6) for _ in range(3)) * 5
        stats["外貌"] = sum(random.randint(1, 6) for _ in range(3)) * 5
        stats["智力"] = (sum(random.randint(1, 6) for _ in range(2)) + 6) * 5
        stats["意志"] = sum(random.randint(1, 6) for _ in range(3)) * 5
        stats["教育"] = (sum(random.randint(1, 6) for _ in range(2)) + 6) * 5
        stats["幸运"] = sum(random.randint(1, 6) for _ in range(3)) * 5
        
        # 衍生属性
        stats["生命值"] = (stats["体型"] + stats["体质"]) // 10
        stats["理智值"] = stats["意志"]
        stats["魔法值"] = stats["意志"] // 5
        
        result = f"🎲 角色{i+1}:\n"
        result += f"力量：{stats['力量']}  体质：{stats['体质']}  体型：{stats['体型']}\n"
        result += f"敏捷：{stats['敏捷']}  外貌：{stats['外貌']}  智力：{stats['智力']}\n"
        result += f"意志：{stats['意志']}  教育：{stats['教育']}  幸运：{stats['幸运']}\n"
        result += f"生命值：{stats['生命值']}  理智值：{stats['理智值']}  魔法值：{stats['魔法值']}"
        
        results.append(result)
    
    return "\n\n".join(results)

def cmd_setcoc(message: str, group_id: str, is_group: bool) -> str:
    """设置房规指令"""
    if not is_group:
        return "该指令仅限群聊使用"
    
    parts = message.split()
    if len(parts) == 1:
        return "参数错误！正确格式：.setcoc [0-6] 或 .setcoc show"
    
    subcommand = parts[1]
    
    if subcommand == "show":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT roomrule FROM groups WHERE group_id = ?", (group_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            rule = result[0]
            rule_descriptions = {
                0: "规则书：出1大成功，不满50出96-100大失败，满50出100大失败",
                1: "不满50出1大成功/满50出1-5大成功，不满50出96-100大失败/满50出100大失败",
                2: "出1-5且<=成功率大成功，出100或出96-99且>成功率大失败",
                3: "出1-5大成功，出96-100大失败",
                4: "出1-5且<=成功率/10大成功，不满50出>=96+成功率/10大失败/满50出100大失败",
                5: "出1-2且<成功率/5大成功，不满50出96-100大失败/满50出99-100大失败",
                6: "个位数=十位数且<=成功率则大成功，个位数=十位数且>成功率则大失败"
            }
            return f"当前房规：{rule}\n{rule_descriptions.get(rule, '未知房规')}"
        else:
            return "获取房规失败"
    
    try:
        rule = int(subcommand)
        if rule < 0 or rule > 6:
            return "房规必须在0-6之间"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE groups SET roomrule = ? WHERE group_id = ?", (rule, group_id))
        conn.commit()
        conn.close()
        
        return f"房规已设置为：{rule}"
        
    except ValueError:
        return "参数错误！房规必须是0-6之间的数字"

def cmd_sc(message: str, user_id: str, group_id: str, is_group: bool) -> str:
    """理智检定指令"""
    parts = message.split()
    if len(parts) < 2:
        return "参数错误！正确格式：.sc [成功损失]/[失败损失] (当前san值)"
    
    # 解析损失值
    loss_part = parts[1]
    if "/" not in loss_part:
        return "参数错误！损失值格式：成功损失/失败损失"
    
    try:
        success_loss_str, fail_loss_str = loss_part.split("/")
        success_loss = int(success_loss_str)
        fail_loss = int(fail_loss_str)
    except ValueError:
        return "参数错误！损失值必须是数字"
    
    # 获取SAN值
    current_san = None
    if len(parts) >= 3:
        try:
            current_san = int(parts[2])
        except ValueError:
            return "SAN值必须是数字"
    else:
        # 从角色卡获取
        char_data = get_current_character(user_id, group_id, is_group)
        if not char_data:
            return "未找到角色卡，请提供当前SAN值或先创建角色卡"
        
        check_data = json.loads(char_data[5])
        if "理智" in check_data:
            current_san = check_data["理智"]
        elif "理智值" in check_data:
            current_san = check_data["理智值"]
        elif "SAN" in check_data:
            current_san = check_data["SAN"]
        else:
            return "角色卡中未找到理智值，请提供当前SAN值"
    
    # 进行理智检定
    roll = random.randint(1, 100)
    
    if roll == 100:  # 大失败
        actual_loss = max(success_loss, fail_loss)
        result = f"理智检定：{roll}/100 大失败！"
    elif roll <= current_san:  # 成功
        actual_loss = success_loss
        result = f"理智检定：{roll}/{current_san} 成功"
    else:  # 失败
        actual_loss = fail_loss
        result = f"理智检定：{roll}/{current_san} 失败"
    
    new_san = current_san - actual_loss
    result += f"\n理智损失：{actual_loss}\n当前理智：{current_san} → {new_san}"
    
    # 如果没有提供SAN值参数，更新角色卡
    if len(parts) < 3:
        char_id = char_data[0]
        check_data = json.loads(char_data[5])
        
        # 更新理智值
        if "理智" in check_data:
            check_data["理智"] = new_san
        elif "理智值" in check_data:
            check_data["理智值"] = new_san
        elif "SAN" in check_data:
            check_data["SAN"] = new_san
        else:
            check_data["理智"] = new_san
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE characters SET check_data = ? WHERE id = ?",
                       (json.dumps(check_data), char_id))
        conn.commit()
        conn.close()
        
        result += "\n角色卡已更新"
    
    return result

def cmd_madness() -> str:
    """疯狂症状指令"""
    try:
        with open(CONFIG["madness_file"], 'r', encoding='utf-8') as f:
            madness_data = json.load(f)
        
        # 默认使用临时疯狂表（.ti/.li通常指临时疯狂）
        temp_madness = madness_data.get("temporary_madness", [])
        if not temp_madness:
            return "临时疯狂数据为空"
        
        # 随机选择一个临时疯狂症状
        base_symptom = random.choice(temp_madness)
        
        # 检查是否需要进一步选择
        if "恐惧：从恐惧症状表中随机选择" in base_symptom:
            phobia_list = madness_data.get("phobia_symptoms", [])
            if phobia_list:
                specific_phobia = random.choice(phobia_list)
                return f"🧠 疯狂症状：{specific_phobia}"
            else:
                return "🧠 疯狂症状：恐惧：对未知事物的强烈恐惧"
        
        elif "躁狂：从躁狂症状表中随机选择" in base_symptom:
            mania_list = madness_data.get("mania_symptoms", [])
            if mania_list:
                specific_mania = random.choice(mania_list)
                return f"🧠 疯狂症状：{specific_mania}"
            else:
                return "🧠 疯狂症状：躁狂：表现出异常兴奋和冲动的行为"
        
        else:
            # 直接返回基础症状
            return f"🧠 疯狂症状：{base_symptom}"
        
    except Exception:
        return "读取疯狂症状数据失败"

def cmd_enhance(message: str, user_id: str, group_id: str, is_group: bool) -> str:
    """成长检定指令"""
    parts = message.split()
    if len(parts) < 2:
        return "参数错误！正确格式：.en [技能名称/技能值]"
    
    target = " ".join(parts[1:])
    
    # 尝试解析为数值
    try:
        skill_value = int(target)
        # 直接使用提供的技能值
        return perform_enhancement(skill_value, target)
    except ValueError:
        # 从角色卡查找技能
        char_data = get_current_character(user_id, group_id, is_group)
        if not char_data:
            return "未找到角色卡，请先使用 .pc new 创建"
        
        check_data = json.loads(char_data[5])
        if target not in check_data:
            return f"角色卡中未找到技能：{target}"
        
        current_value = check_data[target]
        if not isinstance(current_value, (int, float)):
            return f"技能 {target} 不是数值类型"
        
        result = perform_enhancement(int(current_value), target)
        
        # 更新角色卡
        roll = random.randint(1, 100)
        if roll > current_value and roll <= 95:
            enhancement = random.randint(1, 10)
            new_value = current_value + enhancement
            check_data[target] = new_value
            
            char_id = char_data[0]
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE characters SET check_data = ? WHERE id = ?",
                           (json.dumps(check_data), char_id))
            conn.commit()
            conn.close()
            
            result += f"\n技能已更新：{current_value} → {new_value}"
        
        return result

def perform_enhancement(skill_value: int, skill_name: str) -> str:
    """执行成长检定"""
    roll = random.randint(1, 100)
    
    if roll > skill_value and roll <= 95:
        enhancement = random.randint(1, 10)
        return f"成长检定：{roll} > {skill_value}，成功！\n{skill_name} 成长 {enhancement} 点"
    else:
        if roll <= skill_value:
            return f"成长检定：{roll} <= {skill_value}，失败\n{skill_name} 没有成长"
        else:  # roll > 95
            return f"成长检定：{roll} > 95，大失败\n{skill_name} 没有成长"

# ================================
# 角色卡管理函数
# ================================

def cmd_pc(message: str, user_id: str, group_id: str, is_group: bool) -> str:
    """角色卡管理指令"""
    parts = message.split()
    if len(parts) < 2:
        return "参数错误！使用 .help pc 查看详细用法"
    
    subcommand = parts[1]
    
    if subcommand == "new":
        return pc_new(parts, user_id, group_id, is_group)
    elif subcommand == "tag":
        return pc_tag(parts, user_id, group_id, is_group)
    elif subcommand == "show":
        return pc_show(parts, user_id, group_id, is_group)
    elif subcommand == "del":
        return pc_del(parts, user_id)
    elif subcommand == "list":
        return pc_list(user_id)
    elif subcommand == "clr":
        return pc_clear(user_id)
    else:
        return "未知子命令！使用 .help pc 查看可用命令"

def pc_new(parts: List[str], user_id: str, group_id: str, is_group: bool) -> str:
    """新建角色卡"""
    if len(parts) < 3:
        return "参数错误！正确格式：.pc new [名称]"
    
    char_name = " ".join(parts[2:])
    if len(char_name) > CONFIG["max_name_length"]:
        return f"角色卡名称长度不能超过{CONFIG['max_name_length']}字符"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        shown_id = get_next_shown_id(user_id)
        
        cursor.execute("""
            INSERT INTO characters (name, user_id, shown_id, check_data, flavor_data)
            VALUES (?, ?, ?, '{}', '{}')
        """, (char_name, user_id, shown_id))
        
        char_id = cursor.lastrowid
        
        # 如果用户无全局默认卡，设为默认
        cursor.execute("SELECT char_id FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone()[0]:  # char_id为None
            cursor.execute("UPDATE users SET char_id = ? WHERE user_id = ?", (char_id, user_id))
        
        # 如果在群聊中，设为群聊默认
        if is_group:
            cursor.execute("UPDATE group_users SET char_id = ? WHERE user_id = ? AND group_id = ?",
                           (char_id, user_id, group_id))
        
        conn.commit()
        return f"角色卡 {char_name}({shown_id:04d}) 创建成功"
        
    except sqlite3.IntegrityError:
        return "角色卡创建失败"
    finally:
        conn.close()

def pc_tag(parts: List[str], user_id: str, group_id: str, is_group: bool) -> str:
    """绑定角色卡"""
    if len(parts) < 3:
        # 解除绑定
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if is_group:
            cursor.execute("UPDATE group_users SET char_id = NULL WHERE user_id = ? AND group_id = ?",
                           (user_id, group_id))
        else:
            cursor.execute("UPDATE users SET char_id = NULL WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        return "已解除角色卡绑定"
    
    identifier = " ".join(parts[2:])
    char_data = find_character(user_id, identifier)
    
    if not char_data:
        return "未找到指定角色卡"
    
    char_id, char_name = char_data[0], char_data[1]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if is_group:
        cursor.execute("UPDATE group_users SET char_id = ?, nickname = ? WHERE user_id = ? AND group_id = ?",
                       (char_id, char_name, user_id, group_id))
        msg = f"已将 {char_name} 绑定为群聊默认角色卡，并设置为群聊昵称"
    else:
        cursor.execute("UPDATE users SET char_id = ? WHERE user_id = ?", (char_id, user_id))
        msg = f"已将 {char_name} 绑定为全局默认角色卡"
    
    conn.commit()
    conn.close()
    
    return msg

def pc_show(parts: List[str], user_id: str, group_id: str, is_group: bool) -> str:
    """显示角色卡"""
    if len(parts) < 3:
        # 显示当前默认卡
        char_data = get_current_character(user_id, group_id, is_group)
        if not char_data:
            return "未找到默认角色卡，请先创建或绑定角色卡"
    else:
        identifier = " ".join(parts[2:])
        char_data = find_character(user_id, identifier)
        if not char_data:
            return "未找到指定角色卡"
    
    char_name = char_data[1]
    shown_id = char_data[3]
    check_data = json.loads(char_data[5])
    flavor_data = json.loads(char_data[6])
    
    result = f"📋 {char_name}({shown_id:04d})\n\n"
    
    if check_data:
        result += "📊 检定用属性:\n"
        for attr, value in check_data.items():
            result += f"{attr}: {value}\n"
        result += "\n"
    
    if flavor_data:
        result += "📝 描述信息:\n"
        for attr, value in flavor_data.items():
            result += f"{attr}: {value}\n"
    
    return result.strip()

def pc_del(parts: List[str], user_id: str) -> str:
    """删除角色卡"""
    if len(parts) < 3:
        return "参数错误！正确格式：.pc del [名称/编号]"
    
    identifier = " ".join(parts[2:])
    char_data = find_character(user_id, identifier)
    
    if not char_data:
        return "未找到指定角色卡"
    
    char_id, char_name = char_data[0], char_data[1]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 删除角色卡
    cursor.execute("DELETE FROM characters WHERE id = ?", (char_id,))
    
    # 清理相关引用
    cursor.execute("UPDATE users SET char_id = NULL WHERE char_id = ?", (char_id,))
    cursor.execute("UPDATE group_users SET char_id = NULL WHERE char_id = ?", (char_id,))
    
    conn.commit()
    conn.close()
    
    return f"角色卡 {char_name} 已删除"

def pc_list(user_id: str) -> str:
    """列出角色卡"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, shown_id FROM characters WHERE user_id = ? ORDER BY shown_id",
                   (user_id,))
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        return "您还没有创建任何角色卡"
    
    result = "📋 您的角色卡列表:\n"
    for name, shown_id in results:
        result += f"{name}({shown_id:04d})\n"
    
    return result.strip()

def pc_clear(user_id: str) -> str:
    """清空角色卡"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 删除所有角色卡
    cursor.execute("DELETE FROM characters WHERE user_id = ?", (user_id,))
    
    # 清理相关引用
    cursor.execute("UPDATE users SET char_id = NULL WHERE user_id = ?", (user_id,))
    cursor.execute("UPDATE group_users SET char_id = NULL WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()
    
    return "已清空所有角色卡"

# ================================
# 属性管理函数
# ================================

def cmd_st(message: str, user_id: str, group_id: str, is_group: bool) -> str:
    """属性录入指令"""
    parts = message.split()
    if len(parts) < 2:
        return "参数错误！使用 .help st 查看详细用法"
    
    subcommand = parts[1]
    
    if subcommand == "show":
        return st_show(parts, user_id, group_id, is_group)
    elif subcommand == "del":
        return st_del(parts, user_id, group_id, is_group)
    elif subcommand == "clr":
        return st_clear(user_id, group_id, is_group)
    else:
        # 设置属性
        return st_set(parts, user_id, group_id, is_group)

def st_set(parts: List[str], user_id: str, group_id: str, is_group: bool) -> str:
    """设置属性"""
    if len(parts) < 3:
        return "参数错误！正确格式：.st [属性] [数值/字符串] 或 .st 智力80攀爬20..."
    
    # 检查是否是修改操作
    if len(parts) == 4 and parts[2] in ["+", "-"]:
        return st_modify(parts[1], parts[2], parts[3], user_id, group_id, is_group)
    
    # 合并所有参数（去掉 .st）
    full_input = "".join(parts[1:])
    
    # 尝试解析多属性格式：字符+数字+字符+数字...
    multi_attr_pattern = r'([a-zA-Z\u4e00-\u9fff]+)(\d+)'
    matches = re.findall(multi_attr_pattern, full_input)
    
    if matches and len(matches) >= 2:
        # 多属性设置模式
        return st_set_multiple(matches, user_id, group_id, is_group)
    else:
        # 单属性设置模式（原有逻辑）
        attr_name = parts[1]
        attr_value = " ".join(parts[2:])
        return st_set_single(attr_name, attr_value, user_id, group_id, is_group)

def st_set_multiple(attr_pairs: List[Tuple[str, str]], user_id: str, group_id: str, is_group: bool) -> str:
    """设置多个属性"""
    # 确保有角色卡
    char_data = get_current_character(user_id, group_id, is_group)
    if not char_data:
        # 自动创建角色卡
        shown_id = get_next_shown_id(user_id)
        char_name = f"角色卡{shown_id:04d}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO characters (name, user_id, shown_id, check_data, flavor_data)
            VALUES (?, ?, ?, '{}', '{}')
        """, (char_name, user_id, shown_id))
        
        char_id = cursor.lastrowid
        
        # 设为默认卡
        cursor.execute("UPDATE users SET char_id = ? WHERE user_id = ?", (char_id, user_id))
        if is_group:
            cursor.execute("UPDATE group_users SET char_id = ? WHERE user_id = ? AND group_id = ?",
                           (char_id, user_id, group_id))
        
        conn.commit()
        conn.close()
        
        char_data = (char_id, char_name, user_id, shown_id, 'coc7', '{}', '{}')
    
    char_id = char_data[0]
    check_data = json.loads(char_data[5])
    flavor_data = json.loads(char_data[6])
    
    # 处理所有属性
    results = []
    for attr_name, attr_value in attr_pairs:
        try:
            # 尝试转换为数值
            numeric_value = float(attr_value)
            if numeric_value.is_integer():
                numeric_value = int(numeric_value)
            check_data[attr_name] = numeric_value
            results.append(f"{attr_name}:{numeric_value}")
        except ValueError:
            # 如果转换失败，存为字符串
            flavor_data[attr_name] = attr_value
            results.append(f"{attr_name}:{attr_value}")
    
    # 保存到数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE characters SET check_data = ?, flavor_data = ? WHERE id = ?",
                   (json.dumps(check_data), json.dumps(flavor_data), char_id))
    conn.commit()
    conn.close()
    
    return f"已设置属性：{' '.join(results)}"

def st_set_single(attr_name: str, attr_value: str, user_id: str, group_id: str, is_group: bool) -> str:
    """设置单个属性（原有逻辑）"""
    # 确保有角色卡
    char_data = get_current_character(user_id, group_id, is_group)
    if not char_data:
        # 自动创建角色卡
        shown_id = get_next_shown_id(user_id)
        char_name = f"角色卡{shown_id:04d}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO characters (name, user_id, shown_id, check_data, flavor_data)
            VALUES (?, ?, ?, '{}', '{}')
        """, (char_name, user_id, shown_id))
        
        char_id = cursor.lastrowid
        
        # 设为默认卡
        cursor.execute("UPDATE users SET char_id = ? WHERE user_id = ?", (char_id, user_id))
        if is_group:
            cursor.execute("UPDATE group_users SET char_id = ? WHERE user_id = ? AND group_id = ?",
                           (char_id, user_id, group_id))
        
        conn.commit()
        conn.close()
        
        char_data = (char_id, char_name, user_id, shown_id, 'coc7', '{}', '{}')
    
    char_id = char_data[0]
    check_data = json.loads(char_data[5])
    flavor_data = json.loads(char_data[6])
    
    # 判断是数值还是字符串
    try:
        numeric_value = float(attr_value)
        if numeric_value.is_integer():
            numeric_value = int(numeric_value)
        check_data[attr_name] = numeric_value
        target_data = check_data
    except ValueError:
        flavor_data[attr_name] = attr_value
        target_data = flavor_data
    
    # 保存到数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE characters SET check_data = ?, flavor_data = ? WHERE id = ?",
                   (json.dumps(check_data), json.dumps(flavor_data), char_id))
    conn.commit()
    conn.close()
    
    return f"属性 {attr_name} 已设置为 {attr_value}"

def st_modify(attr_name: str, operation: str, value_str: str, user_id: str, group_id: str, is_group: bool) -> str:
    """修改数值属性"""
    char_data = get_current_character(user_id, group_id, is_group)
    if not char_data:
        return "未找到角色卡，请先使用 .pc new 创建"
    
    try:
        modify_value = float(value_str)
        if modify_value.is_integer():
            modify_value = int(modify_value)
    except ValueError:
        return "修改值必须是数字"
    
    char_id = char_data[0]
    check_data = json.loads(char_data[5])
    
    if attr_name not in check_data:
        return f"属性 {attr_name} 不存在"
    
    current_value = check_data[attr_name]
    if not isinstance(current_value, (int, float)):
        return f"属性 {attr_name} 不是数值类型，无法进行加减运算"
    
    if operation == "+":
        new_value = current_value + modify_value
    else:  # operation == "-"
        new_value = current_value - modify_value
    
    check_data[attr_name] = new_value
    
    # 保存到数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE characters SET check_data = ? WHERE id = ?",
                   (json.dumps(check_data), char_id))
    conn.commit()
    conn.close()
    
    return f"属性 {attr_name}: {current_value} {operation} {modify_value} = {new_value}"

def st_show(parts: List[str], user_id: str, group_id: str, is_group: bool) -> str:
    """显示属性"""
    char_data = get_current_character(user_id, group_id, is_group)
    if not char_data:
        return "未找到角色卡，请先使用 .pc new 创建"
    
    check_data = json.loads(char_data[5])
    flavor_data = json.loads(char_data[6])
    
    if len(parts) >= 3:
        # 显示特定属性
        attr_name = parts[2]
        if attr_name in check_data:
            return f"{attr_name}: {check_data[attr_name]}"
        elif attr_name in flavor_data:
            return f"{attr_name}: {flavor_data[attr_name]}"
        else:
            return f"属性 {attr_name} 不存在"
    else:
        # 显示所有属性
        result = f"📋 {char_data[1]} 的属性:\n\n"
        
        if check_data:
            result += "📊 检定用属性:\n"
            for attr, value in check_data.items():
                result += f"{attr}: {value}\n"
            result += "\n"
        
        if flavor_data:
            result += "📝 描述信息:\n"
            for attr, value in flavor_data.items():
                result += f"{attr}: {value}\n"
        
        return result.strip()

def st_del(parts: List[str], user_id: str, group_id: str, is_group: bool) -> str:
    """删除属性"""
    if len(parts) < 3:
        return "参数错误！正确格式：.st del [属性]"
    
    char_data = get_current_character(user_id, group_id, is_group)
    if not char_data:
        return "未找到角色卡，请先使用 .pc new 创建"
    
    attr_name = parts[2]
    char_id = char_data[0]
    check_data = json.loads(char_data[5])
    flavor_data = json.loads(char_data[6])
    
    found = False
    if attr_name in check_data:
        del check_data[attr_name]
        found = True
    if attr_name in flavor_data:
        del flavor_data[attr_name]
        found = True
    
    if not found:
        return f"属性 {attr_name} 不存在"
    
    # 保存到数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE characters SET check_data = ?, flavor_data = ? WHERE id = ?",
                   (json.dumps(check_data), json.dumps(flavor_data), char_id))
    conn.commit()
    conn.close()
    
    return f"属性 {attr_name} 已删除"

def st_clear(user_id: str, group_id: str, is_group: bool) -> str:
    """清空属性"""
    char_data = get_current_character(user_id, group_id, is_group)
    if not char_data:
        return "未找到角色卡，请先使用 .pc new 创建"
    
    char_id = char_data[0]
    
    # 清空所有属性
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE characters SET check_data = '{}', flavor_data = '{}' WHERE id = ?",
                   (char_id,))
    conn.commit()
    conn.close()
    
    return "已清空所有属性"
