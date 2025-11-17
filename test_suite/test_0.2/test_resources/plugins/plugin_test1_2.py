# plugin_test1_2.py - 测试所有事件类型的string返回值

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

# MESSAGE事件处理函数 - 支持string返回值
def handle_message_private():
    return "MESSAGE_PRIVATE string response"

def handle_message_group():
    return "MESSAGE_GROUP string response"

def handle_message_group_mention():
    return "MESSAGE_GROUP_MENTION string response"

def handle_message_group_bot():
    return "MESSAGE_GROUP_BOT string response"

def handle_message_sent_private():
    return "MESSAGE_SENT_PRIVATE string response"

def handle_message_sent_group():
    return "MESSAGE_SENT_GROUP string response"

# NOTICE事件处理函数 - 部分支持string返回值
def handle_notice_friend_add():
    return "NOTICE_FRIEND_ADD string response"

def handle_notice_friend_recall():
    return "NOTICE_FRIEND_RECALL string response"

def handle_notice_group_recall():
    return "NOTICE_GROUP_RECALL string response"

def handle_notice_group_increase():
    return "NOTICE_GROUP_INCREASE string response"

def handle_notice_group_decrease():
    return "NOTICE_GROUP_DECREASE string response"

def handle_notice_group_admin():
    return "NOTICE_GROUP_ADMIN string response"

def handle_notice_group_ban():
    return "NOTICE_GROUP_BAN string response"

def handle_notice_group_upload():
    return "NOTICE_GROUP_UPLOAD string response"

def handle_notice_group_card():
    return "NOTICE_GROUP_CARD string response"

def handle_notice_essence():
    return "NOTICE_ESSENCE string response"

def handle_notice_group_msg_emoji_like():
    return "NOTICE_GROUP_MSG_EMOJI_LIKE string response"

def handle_notice_bot_offline():
    # NOTICE_BOT_OFFLINE不支持任何返回值
    return "NOTICE_BOT_OFFLINE string response"

def handle_notice_group_name():
    return "NOTICE_GROUP_NAME string response"

def handle_notice_group_title():
    return "NOTICE_GROUP_TITLE string response"

def handle_notice_poke():
    return "NOTICE_POKE string response"

def handle_notice_profile_like():
    return "NOTICE_PROFILE_LIKE string response"

def handle_notice_input_status():
    # INPUT_STATUS 通常被框架跳过
    return "NOTICE_INPUT_STATUS string response"

# REQUEST事件处理函数
def handle_request_friend():
    # REQUEST_FRIEND不支持string返回值
    return "REQUEST_FRIEND string response"

def handle_request_group():
    return "REQUEST_GROUP string response"

# META事件处理函数 - 不支持string返回值
def handle_meta_heartbeat():
    return "META_HEARTBEAT string response"

def handle_meta_lifecycle():
    return "META_LIFECYCLE string response"

# UNCONDITIONAL事件处理函数 - 不支持string返回值
def handle_unconditional():
    return "UNCONDITIONAL string response"
