# plugin_test1_1.py - 测试所有事件类型的dict返回值

MANIFEST = {
    "MESSAGE_PRIVATE": "handle_message_private",
    "MESSAGE_GROUP": "handle_message_group",
    "MESSAGE_GROUP_MENTION": "handle_message_group_mention",
    "MESSAGE_GROUP_BOT": "handle_message_group_bot",
    "MESSAGE_SENT_PRIVATE": "handle_message_sent_private",
    "MESSAGE_SENT_GROUP": "handle_message_sent_group",
    "NOTICE_FRIEND_ADD": "handle_notice_friend_add",
    "NOTICE_FRIEND_RECALL": "handle_notice_friend_recall",
    "NOTICE_GROUP_RECALL": "handle_notice_group_recall",
    "NOTICE_GROUP_INCREASE": "handle_notice_group_increase",
    "NOTICE_GROUP_DECREASE": "handle_notice_group_decrease",
    "NOTICE_GROUP_ADMIN": "handle_notice_group_admin",
    "NOTICE_GROUP_BAN": "handle_notice_group_ban",
    "NOTICE_GROUP_UPLOAD": "handle_notice_group_upload",
    "NOTICE_GROUP_CARD": "handle_notice_group_card",
    "NOTICE_ESSENCE": "handle_notice_essence",
    "NOTICE_GROUP_MSG_EMOJI_LIKE": "handle_notice_group_msg_emoji_like",
    "NOTICE_BOT_OFFLINE": "handle_notice_bot_offline",
    "NOTICE_GROUP_NAME": "handle_notice_group_name",
    "NOTICE_GROUP_TITLE": "handle_notice_group_title",
    "NOTICE_POKE": "handle_notice_poke",
    "NOTICE_PROFILE_LIKE": "handle_notice_profile_like",
    "NOTICE_INPUT_STATUS": "handle_notice_input_status",
    "REQUEST_FRIEND": "handle_request_friend",
    "REQUEST_GROUP": "handle_request_group",
    "META_HEARTBEAT": "handle_meta_heartbeat",
    "META_LIFECYCLE": "handle_meta_lifecycle",
    "UNCONDITIONAL": ["handle_unconditional", 1]  # 每分钟执行
}

# 固定的响应目标QQ号
RESPONSE_QQ = 99999999

def create_response(event_type):
    """创建标准的dict响应"""
    return {
        "action": "send_private_msg",
        "data": {
            "user_id": RESPONSE_QQ,
            "message": [
                {
                    "type": "text",
                    "data": {"text": f"{event_type} received"}
                }
            ]
        }
    }

# MESSAGE事件处理函数
def handle_message_private():
    return create_response("MESSAGE_PRIVATE")

def handle_message_group():
    return create_response("MESSAGE_GROUP")

def handle_message_group_mention():
    return create_response("MESSAGE_GROUP_MENTION")

def handle_message_group_bot():
    return create_response("MESSAGE_GROUP_BOT")

def handle_message_sent_private():
    return create_response("MESSAGE_SENT_PRIVATE")

def handle_message_sent_group():
    return create_response("MESSAGE_SENT_GROUP")

# NOTICE事件处理函数
def handle_notice_friend_add():
    return create_response("NOTICE_FRIEND_ADD")

def handle_notice_friend_recall():
    return create_response("NOTICE_FRIEND_RECALL")

def handle_notice_group_recall():
    return create_response("NOTICE_GROUP_RECALL")

def handle_notice_group_increase():
    return create_response("NOTICE_GROUP_INCREASE")

def handle_notice_group_decrease():
    return create_response("NOTICE_GROUP_DECREASE")

def handle_notice_group_admin():
    return create_response("NOTICE_GROUP_ADMIN")

def handle_notice_group_ban():
    return create_response("NOTICE_GROUP_BAN")

def handle_notice_group_upload():
    return create_response("NOTICE_GROUP_UPLOAD")

def handle_notice_group_card():
    return create_response("NOTICE_GROUP_CARD")

def handle_notice_essence():
    return create_response("NOTICE_ESSENCE")

def handle_notice_group_msg_emoji_like():
    return create_response("NOTICE_GROUP_MSG_EMOJI_LIKE")

def handle_notice_bot_offline():
    # NOTICE_BOT_OFFLINE不支持任何返回值
    return None

def handle_notice_group_name():
    return create_response("NOTICE_GROUP_NAME")

def handle_notice_group_title():
    return create_response("NOTICE_GROUP_TITLE")

def handle_notice_poke():
    return create_response("NOTICE_POKE")

def handle_notice_profile_like():
    return create_response("NOTICE_PROFILE_LIKE")

def handle_notice_input_status():
    # INPUT_STATUS 通常被框架跳过，但我们还是注册它
    return create_response("NOTICE_INPUT_STATUS")

# REQUEST事件处理函数
def handle_request_friend():
    # REQUEST_FRIEND不支持字符串返回值，但支持dict
    return None  # 不响应好友请求

def handle_request_group():
    return create_response("REQUEST_GROUP")

# META事件处理函数
def handle_meta_heartbeat():
    return create_response("META_HEARTBEAT")

def handle_meta_lifecycle():
    return create_response("META_LIFECYCLE")

# UNCONDITIONAL事件处理函数
def handle_unconditional():
    return create_response("UNCONDITIONAL")
