#!/usr/bin/env python3
"""
测试插件1：全事件类型测试
为每个事件类型单独注册处理函数，返回硬编码的确认消息
"""

MANIFEST = {
    "MESSAGE_PRIVATE": "handle_message_private",
    "MESSAGE_GROUP": "handle_message_group", 
    "MESSAGE_GROUP_MENTION": "handle_message_group_mention",
    "MESSAGE_GROUP_BOT": "handle_message_group_bot",
    "NOTICE_FRIEND_ADD": "handle_notice_friend_add",
    "NOTICE_FRIEND_RECALL": "handle_notice_friend_recall", 
    "NOTICE_GROUP_RECALL": "handle_notice_group_recall",
    "NOTICE_GROUP_INCREASE": "handle_notice_group_increase",
    "NOTICE_GROUP_DECREASE": "handle_notice_group_decrease",
    "NOTICE_GROUP_ADMIN": "handle_notice_group_admin",
    "NOTICE_GROUP_BAN": "handle_notice_group_ban",
    "NOTICE_GROUP_UPLOAD": "handle_notice_group_upload",
    "NOTICE_GROUP_CARD": "handle_notice_group_card",
    "NOTICE_GROUP_NAME": "handle_notice_group_name",
    "NOTICE_GROUP_TITLE": "handle_notice_group_title",
    "NOTICE_POKE": "handle_notice_poke",
    "NOTICE_PROFILE_LIKE": "handle_notice_profile_like",
    "NOTICE_INPUT_STATUS": "handle_notice_input_status",
    "NOTICE_ESSENCE": "handle_notice_essence",
    "NOTICE_GROUP_MSG_EMOJI_LIKE": "handle_notice_group_msg_emoji_like",
    "NOTICE_BOT_OFFLINE": "handle_notice_bot_offline",
    "REQUEST_FRIEND": "handle_request_friend",
    "REQUEST_GROUP": "handle_request_group"
}

def handle_message_private():
    return "[插件1] MESSAGE_PRIVATE 收到"

def handle_message_group():
    return "[插件1] MESSAGE_GROUP 收到"

def handle_message_group_mention():
    return "[插件1] MESSAGE_GROUP_MENTION 收到"

def handle_message_group_bot():
    return "[插件1] MESSAGE_GROUP_BOT 收到"

def handle_notice_friend_add():
    return "[插件1] NOTICE_FRIEND_ADD 收到"

def handle_notice_friend_recall():
    return "[插件1] NOTICE_FRIEND_RECALL 收到"

def handle_notice_group_recall():
    return "[插件1] NOTICE_GROUP_RECALL 收到"

def handle_notice_group_increase():
    return "[插件1] NOTICE_GROUP_INCREASE 收到"

def handle_notice_group_decrease():
    return "[插件1] NOTICE_GROUP_DECREASE 收到"

def handle_notice_group_admin():
    return "[插件1] NOTICE_GROUP_ADMIN 收到"

def handle_notice_group_ban():
    return "[插件1] NOTICE_GROUP_BAN 收到"

def handle_notice_group_upload():
    return "[插件1] NOTICE_GROUP_UPLOAD 收到"

def handle_notice_group_card():
    return "[插件1] NOTICE_GROUP_CARD 收到"

def handle_notice_group_name():
    return "[插件1] NOTICE_GROUP_NAME 收到"

def handle_notice_group_title():
    return "[插件1] NOTICE_GROUP_TITLE 收到"

def handle_notice_poke():
    return "[插件1] NOTICE_POKE 收到"

def handle_notice_profile_like():
    return "[插件1] NOTICE_PROFILE_LIKE 收到"

def handle_notice_input_status():
    return "[插件1] NOTICE_INPUT_STATUS 收到"

def handle_notice_essence():
    return "[插件1] NOTICE_ESSENCE 收到"

def handle_notice_group_msg_emoji_like():
    return "[插件1] NOTICE_GROUP_MSG_EMOJI_LIKE 收到"

def handle_notice_bot_offline():
    # 注意：BOT_OFFLINE事件不支持字符串返回值，但我们测试框架的处理
    return "[插件1] NOTICE_BOT_OFFLINE 收到"

def handle_request_friend():
    return "[插件1] REQUEST_FRIEND 收到"

def handle_request_group():
    return "[插件1] REQUEST_GROUP 收到"