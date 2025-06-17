"""
调用bilibili-api获取up主动态更新并向粉丝群播报
需要额外的配置文件，/pluginsFile/BiliDynamicsUpdate/BiliDynamicsUpdate.json
内容如下：
{
    "bilibili_credential": {
        "sessdata": "****"#你的b站cookie
    },
    "target_groups": [
        123456789 #粉丝群群号
    ],
    "uid": 3546831533378448, #up的b站uid
    "up_name": "up" #对up的称呼
}
"""
import json
import time
import random
import os
from bilibili_api import user, sync, Credential

MANIFEST = {
    "INITIALIZER": "init_bilibili_monitor",
    "UNCONDITIONAL": ["check_bilibili_dynamics", 2]  # 每2分钟检查一次
}

def init_bilibili_monitor(botContext):
    """
    插件初始化：读取外部配置，验证有效性，初始化框架配置
    """
    try:
        # 检查依赖库
        import bilibili_api
        
        # 读取外部配置文件
        config_file_path = "./pluginsFile/BiliDynamicsUpdate/BiliDynamicsUpdate.json"
        if not os.path.exists(config_file_path):
            raise Exception(f"配置文件 {config_file_path} 不存在")
        
        with open(config_file_path, 'r', encoding='utf-8') as f:
            external_config = json.load(f)
        
        # 验证配置完整性
        required_keys = ["bilibili_credential", "target_groups", "uid", "up_name"]
        for key in required_keys:
            if key not in external_config:
                raise Exception(f"配置文件缺少必要字段: {key}")
        
        if "sessdata" not in external_config["bilibili_credential"]:
            raise Exception("配置文件缺少 bilibili_credential.sessdata")
        
        if not external_config["target_groups"] or not isinstance(external_config["target_groups"], list):
            raise Exception("target_groups 必须是非空列表")
        
        if not external_config["up_name"] or not isinstance(external_config["up_name"], str):
            raise Exception("up_name 必须是非空字符串")
        
        # 验证B站API凭证
        cre = Credential(sessdata=external_config["bilibili_credential"]["sessdata"])
        u = user.User(uid=external_config["uid"], credential=cre)
        
        # 获取初始动态状态
        try:
            # 使用sync同步调用而不是asyncio.run
            dynamics = sync(u.get_dynamics_new())["items"]
            if not dynamics:
                raise Exception("无法获取动态列表")
            
            # 检查是否有置顶动态
            has_pinned = dynamics[0]["modules"].get("module_tag") == {"text": "置顶"}
            if not has_pinned:
                raise Exception("未找到置顶动态，请确认UP主设置")
            
            known_top = dynamics[0]["id_str"]
            last_dynamics = dynamics[1]["id_str"] if len(dynamics) > 1 else ""
            
        except Exception as e:
            raise Exception(f"初始化动态状态失败: {str(e)}")
        
        # 初始化框架配置
        internal_config = {
            "bilibili_credential": external_config["bilibili_credential"],
            "target_groups": external_config["target_groups"],
            "uid": external_config["uid"],
            "up_name": external_config["up_name"],
            "known_top": known_top,
            "last_dynamics": last_dynamics,
            "consecutive_fail_count": 0
        }
        
        botContext["ConfigWriter"](internal_config)
        
        print("B站动态监控插件初始化成功")
        return None
        
    except Exception as e:
        print(f"B站动态监控插件初始化失败: {str(e)}")
        raise e

def check_bilibili_dynamics(rawEvent, botContext):
    """
    定时检查B站动态更新
    """
    config = botContext["ConfigReader"]()
    consecutive_fail_count = config["consecutive_fail_count"]
    
    # 检查是否已禁用服务
    if consecutive_fail_count == 3:
        # 刚好达到3次，通知后进入禁用状态
        config["consecutive_fail_count"] = 4
        botContext["ConfigWriter"](config)
        raise Exception("B站动态播报连续三次异常，已禁用服务")
    
    elif consecutive_fail_count > 3:
        # 已禁用，直接跳过
        return None
    
    # 正常执行检查逻辑
    try:
        # 初始化B站API客户端
        cre = Credential(sessdata=config["bilibili_credential"]["sessdata"])
        u = user.User(uid=config["uid"], credential=cre)
        
        # 使用sync同步获取最新动态
        dynamics = sync(u.get_dynamics_new())["items"]
        
        if not dynamics:
            config["consecutive_fail_count"] += 1
            botContext["ConfigWriter"](config)
            raise Exception("获取动态列表为空")
        
        messages = []
        config_updated = False
        up_name = config["up_name"]  # 读取UP主名称
        
        # 检查置顶动态
        if dynamics[0]["modules"].get("module_tag") != {"text": "置顶"}:
            # 置顶动态消失
            messages.extend(create_messages(config["target_groups"], f"咦？{up_name}的置顶动态不见了？"))
        
        else:
            # 检查置顶动态是否更换
            if dynamics[0]["id_str"] != config["known_top"]:
                config["known_top"] = dynamics[0]["id_str"]
                config_updated = True
                message = f"{up_name}更换了置顶动态！https://t.bilibili.com/{config['known_top']}"
                messages.extend(create_messages(config["target_groups"], message))
            
            # 检查最新动态
            elif len(dynamics) > 1 and dynamics[1]["id_str"] != config["last_dynamics"]:
                dynamic_type = dynamics[1].get("type")
                
                if dynamic_type == "DYNAMIC_TYPE_LIVE_RCMD":
                    # 直播推荐，等待5分钟后再检查（这里只是记录，不实际等待）
                    pass
                
                elif dynamic_type == "DYNAMIC_TYPE_AV":
                    # 新视频
                    config["last_dynamics"] = dynamics[1]["id_str"]
                    config_updated = True
                    
                    try:
                        title = dynamics[1]["modules"]["module_dynamic"]["major"]["archive"]["title"]
                        bvid = dynamics[1]["modules"]["module_dynamic"]["major"]["archive"]["bvid"]
                        message = f"{up_name}发布了新视频：{title}\nhttps://www.bilibili.com/video/{bvid}"
                        messages.extend(create_messages(config["target_groups"], message))
                    except:
                        message = f"{up_name}大抵是发布了新视频（直播回放）..."
                        messages.extend(create_messages(config["target_groups"], message))
                
                elif dynamic_type == "DYNAMIC_TYPE_DRAW":
                    # 图文动态
                    config["last_dynamics"] = dynamics[1]["id_str"]
                    config_updated = True
                    
                    try:
                        title = dynamics[1]["modules"]["module_dynamic"]["major"]["opus"]["title"]
                        link = dynamics[1]["modules"]["module_dynamic"]["major"]["opus"]["jump_url"]
                        message = f"{up_name}发布了新动态：{title}\n{link}"
                        messages.extend(create_messages(config["target_groups"], message))
                    except:
                        message = f"{up_name}大抵是发布了新动态..."
                        messages.extend(create_messages(config["target_groups"], message))
                
                elif dynamic_type == "DYNAMIC_TYPE_FORWARD":
                    # 转发动态
                    config["last_dynamics"] = dynamics[1]["id_str"]
                    config_updated = True
                    message = f"{up_name}转发了一条动态..."
                    messages.extend(create_messages(config["target_groups"], message))
                
                else:
                    # 未知类型
                    config["last_dynamics"] = dynamics[1]["id_str"]
                    config_updated = True
                    message = f"{up_name}大抵是发布了新动态..."
                    messages.extend(create_messages(config["target_groups"], message))
        
        # 成功执行，重置失败计数
        config["consecutive_fail_count"] = 0
        config_updated = True
        
        # 更新配置
        if config_updated:
            botContext["ConfigWriter"](config)
        
        # 返回要发送的消息
        return messages if messages else None
        
    except Exception as e:
        # 失败则计数+1
        config["consecutive_fail_count"] += 1
        botContext["ConfigWriter"](config)
        raise e  # 重新抛出异常，让框架处理通知

def create_messages(target_groups, text):
    """
    为所有目标群创建消息列表
    """
    messages = []
    for group_id in target_groups:
        messages.append({
            "action": "send_group_msg",
            "data": {
                "group_id": group_id,
                "message": [{"type": "text", "data": {"text": text}}]
            }
        })
    return messages
