# 事件完整参考

本文档详细说明 NapCat 支持的所有事件类型及其数据结构。

## 事件基础说明

### 基础字段

所有事件都包含以下基础字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳（秒） |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | 事件类型 |

### 事件类型

| post_type | 说明 |
|-----------|------|
| `message` | 消息事件 |
| `message_sent` | 消息发送事件 |
| `notice` | 通知事件 |
| `request` | 请求事件 |
| `meta_event` | 元事件 |

---

## 消息事件

消息事件的 `post_type` 为 `message`。

### 私聊消息

**事件数据：**

| 字段名 | 类型 | 可能的值 | 说明 |
|--------|------|----------|------|
| `time` | number | - | 事件发生的时间戳 |
| `self_id` | number | - | 收到事件的机器人QQ号 |
| `post_type` | string | `message` | 上报类型 |
| `message_type` | string | `private` | 消息类型 |
| `sub_type` | string | `friend`、`group`、`other` | 消息子类型 |
| `message_id` | number | - | 消息ID |
| `user_id` | number | - | 发送者QQ号 |
| `message` | array | - | 消息内容（消息段数组） |
| `raw_message` | string | - | 原始消息内容 |
| `font` | number | - | 字体 |
| `sender` | object | - | 发送人信息 |

**sender 字段（私聊）：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `user_id` | number | 发送者QQ号 |
| `nickname` | string | 昵称 |
| `sex` | string | 性别：`male`、`female`、`unknown` |
| `age` | number | 年龄 |

**示例：**

```json
{
  "time": 1718000000,
  "self_id": 123456789,
  "post_type": "message",
  "message_type": "private",
  "sub_type": "friend",
  "message_id": 1001,
  "user_id": 234567890,
  "message": [
    {
      "type": "text",
      "data": {
        "text": "你好"
      }
    }
  ],
  "raw_message": "你好",
  "font": 0,
  "sender": {
    "user_id": 234567890,
    "nickname": "小明",
    "sex": "male",
    "age": 18
  }
}
```

### 群消息

**事件数据：**

| 字段名 | 类型 | 可能的值 | 说明 |
|--------|------|----------|------|
| `time` | number | - | 事件发生的时间戳 |
| `self_id` | number | - | 收到事件的机器人QQ号 |
| `post_type` | string | `message` | 上报类型 |
| `message_type` | string | `group` | 消息类型 |
| `sub_type` | string | `normal`、`anonymous`、`notice` | 消息子类型 |
| `message_id` | number | - | 消息ID |
| `group_id` | number | - | 群号 |
| `user_id` | number | - | 发送者QQ号 |
| `anonymous` | object/null | - | 匿名信息 |
| `message` | array | - | 消息内容（消息段数组） |
| `raw_message` | string | - | 原始消息内容 |
| `font` | number | - | 字体 |
| `sender` | object | - | 发送人信息 |

**anonymous 字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | number | 匿名用户ID |
| `name` | string | 匿名用户名称 |
| `flag` | string | 匿名用户flag |

**sender 字段（群聊）：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `user_id` | number | 发送者QQ号 |
| `nickname` | string | 昵称 |
| `card` | string | 群名片/备注 |
| `sex` | string | 性别：`male`、`female`、`unknown` |
| `age` | number | 年龄 |
| `area` | string | 地区 |
| `level` | string | 成员等级 |
| `role` | string | 角色：`owner`、`admin`、`member` |
| `title` | string | 专属头衔 |

**示例：**

```json
{
  "time": 1718000001,
  "self_id": 123456789,
  "post_type": "message",
  "message_type": "group",
  "sub_type": "normal",
  "message_id": 2002,
  "group_id": 987654321,
  "user_id": 345678901,
  "anonymous": null,
  "message": [
    {
      "type": "at",
      "data": {
        "qq": "123456789"
      }
    },
    {
      "type": "text",
      "data": {
        "text": " 大家好！"
      }
    }
  ],
  "raw_message": "[CQ:at,qq=123456789] 大家好！",
  "font": 0,
  "sender": {
    "user_id": 345678901,
    "nickname": "群友A",
    "card": "管理员",
    "sex": "female",
    "age": 20,
    "role": "admin"
  }
}
```

---

## 消息发送事件

消息发送事件的 `post_type` 为 `message_sent`，字段与对应的消息事件基本相同。

### 私聊消息发送

字段与私聊消息事件相同，`post_type` 为 `message_sent`。

### 群消息发送

字段与群消息事件相同，`post_type` 为 `message_sent`。

---

## 通知事件

通知事件的 `post_type` 为 `notice`。

### 群文件上传

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` |
| `notice_type` | string | `group_upload` |
| `group_id` | number | 群号 |
| `user_id` | number | 发送者QQ号 |
| `file` | object | 文件信息 |

**file 字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | string | 文件ID |
| `name` | string | 文件名 |
| `size` | number | 文件大小（字节） |
| `busid` | number | 文件总线ID |

**示例：**

```json
{
  "time": 1718000010,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "group_upload",
  "group_id": 987654321,
  "user_id": 345678901,
  "file": {
    "id": "file_id_123",
    "name": "document.pdf",
    "size": 1048576,
    "busid": 102
  }
}
```

### 群管理员变动

**事件数据：**

| 字段名 | 类型 | 可能的值 | 说明 |
|--------|------|----------|------|
| `time` | number | - | 事件发生的时间戳 |
| `self_id` | number | - | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` | 上报类型 |
| `notice_type` | string | `group_admin` | 通知类型 |
| `sub_type` | string | `set`、`unset` | 事件子类型 |
| `group_id` | number | - | 群号 |
| `user_id` | number | - | 管理员QQ号 |

**示例：**

```json
{
  "time": 1718000011,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "group_admin",
  "sub_type": "set",
  "group_id": 987654321,
  "user_id": 345678901
}
```

### 群成员减少

**事件数据：**

| 字段名 | 类型 | 可能的值 | 说明 |
|--------|------|----------|------|
| `time` | number | - | 事件发生的时间戳 |
| `self_id` | number | - | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` | 上报类型 |
| `notice_type` | string | `group_decrease` | 通知类型 |
| `sub_type` | string | `leave`、`kick`、`kick_me` | 事件子类型 |
| `group_id` | number | - | 群号 |
| `operator_id` | number | - | 操作者QQ号 |
| `user_id` | number | - | 离开者QQ号 |

**示例：**

```json
{
  "time": 1718000012,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "group_decrease",
  "sub_type": "kick",
  "group_id": 987654321,
  "operator_id": 111111111,
  "user_id": 222222222
}
```

### 群成员增加

**事件数据：**

| 字段名 | 类型 | 可能的值 | 说明 |
|--------|------|----------|------|
| `time` | number | - | 事件发生的时间戳 |
| `self_id` | number | - | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` | 上报类型 |
| `notice_type` | string | `group_increase` | 通知类型 |
| `sub_type` | string | `approve`、`invite` | 事件子类型 |
| `group_id` | number | - | 群号 |
| `operator_id` | number | - | 操作者QQ号 |
| `user_id` | number | - | 加入者QQ号 |

**示例：**

```json
{
  "time": 1718000013,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "group_increase",
  "sub_type": "invite",
  "group_id": 987654321,
  "operator_id": 111111111,
  "user_id": 333333333
}
```

### 群禁言

**事件数据：**

| 字段名 | 类型 | 可能的值 | 说明 |
|--------|------|----------|------|
| `time` | number | - | 事件发生的时间戳 |
| `self_id` | number | - | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` | 上报类型 |
| `notice_type` | string | `group_ban` | 通知类型 |
| `sub_type` | string | `ban`、`lift_ban` | 事件子类型 |
| `group_id` | number | - | 群号 |
| `operator_id` | number | - | 操作者QQ号 |
| `user_id` | number | - | 被禁言QQ号 |
| `duration` | number | - | 禁言时长（秒） |

**示例：**

```json
{
  "time": 1718000014,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "group_ban",
  "sub_type": "ban",
  "group_id": 987654321,
  "operator_id": 111111111,
  "user_id": 444444444,
  "duration": 600
}
```

### 好友添加

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` |
| `notice_type` | string | `friend_add` |
| `user_id` | number | 新好友QQ号 |

**示例：**

```json
{
  "time": 1718000015,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "friend_add",
  "user_id": 555555555
}
```

### 群消息撤回

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` |
| `notice_type` | string | `group_recall` |
| `group_id` | number | 群号 |
| `user_id` | number | 消息发送者QQ号 |
| `operator_id` | number | 操作者QQ号 |
| `message_id` | number | 被撤回的消息ID |

**示例：**

```json
{
  "time": 1718000016,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "group_recall",
  "group_id": 987654321,
  "user_id": 666666666,
  "operator_id": 111111111,
  "message_id": 12345
}
```

### 好友消息撤回

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` |
| `notice_type` | string | `friend_recall` |
| `user_id` | number | 消息发送者QQ号 |
| `message_id` | number | 被撤回的消息ID |

**示例：**

```json
{
  "time": 1718000017,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "friend_recall",
  "user_id": 777777777,
  "message_id": 67890
}
```

### 群名片变更

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` |
| `notice_type` | string | `group_card` |
| `group_id` | number | 群号 |
| `user_id` | number | 成员QQ号 |
| `card_new` | string | 新名片 |
| `card_old` | string | 旧名片 |

**示例：**

```json
{
  "time": 1718000018,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "group_card",
  "group_id": 987654321,
  "user_id": 888888888,
  "card_new": "新昵称",
  "card_old": "旧昵称"
}
```

### 群精华消息

**事件数据：**

| 字段名 | 类型 | 可能的值 | 说明 |
|--------|------|----------|------|
| `time` | number | - | 事件发生的时间戳 |
| `self_id` | number | - | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` | 上报类型 |
| `notice_type` | string | `essence` | 通知类型 |
| `sub_type` | string | `add`、`delete` | 事件子类型 |
| `group_id` | number | - | 群号 |
| `sender_id` | number | - | 消息发送者QQ号 |
| `operator_id` | number | - | 操作者QQ号 |
| `message_id` | number | - | 消息ID |

**示例：**

```json
{
  "time": 1718000019,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "essence",
  "sub_type": "add",
  "group_id": 987654321,
  "sender_id": 999999999,
  "operator_id": 111111111,
  "message_id": 54321
}
```

### 群表情回应

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` |
| `notice_type` | string | `group_msg_emoji_like` |
| `group_id` | number | 群号 |
| `user_id` | number | 发送者QQ号 |
| `message_id` | number | 消息ID |
| `likes` | array | 表情信息列表 |

**likes 数组元素：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `emoji_id` | string | 表情ID |
| `count` | number | 回应数量 |

**示例：**

```json
{
  "time": 1718000020,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "group_msg_emoji_like",
  "group_id": 987654321,
  "user_id": 111222333,
  "message_id": 11111,
  "likes": [
    {
      "emoji_id": "123",
      "count": 5
    }
  ]
}
```

### 戳一戳（好友）

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` |
| `notice_type` | string | `notify` |
| `sub_type` | string | `poke` |
| `sender_id` | number | 发送者QQ号 |
| `user_id` | number | 发送者QQ号 |
| `target_id` | number | 被戳者QQ号 |

**示例：**

```json
{
  "time": 1718000021,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "notify",
  "sub_type": "poke",
  "sender_id": 444555666,
  "user_id": 444555666,
  "target_id": 123456789
}
```

### 戳一戳（群聊）

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` |
| `notice_type` | string | `notify` |
| `sub_type` | string | `poke` |
| `group_id` | number | 群号 |
| `user_id` | number | 发送者QQ号 |
| `target_id` | number | 被戳者QQ号 |

**示例：**

```json
{
  "time": 1718000022,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "notify",
  "sub_type": "poke",
  "group_id": 987654321,
  "user_id": 777888999,
  "target_id": 123456789
}
```

### 群头衔变更

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` |
| `notice_type` | string | `notify` |
| `sub_type` | string | `title` |
| `group_id` | number | 群号 |
| `user_id` | number | 成员QQ号 |
| `title` | string | 新头衔 |

**示例：**

```json
{
  "time": 1718000023,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "notify",
  "sub_type": "title",
  "group_id": 987654321,
  "user_id": 111222333,
  "title": "活跃之星"
}
```

### 个人资料点赞

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` |
| `notice_type` | string | `notify` |
| `sub_type` | string | `profile_like` |
| `operator_id` | number | 操作者QQ号 |
| `operator_nick` | string | 操作者昵称 |
| `times` | number | 点赞次数 |

**示例：**

```json
{
  "time": 1718000024,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "notify",
  "sub_type": "profile_like",
  "operator_id": 444555666,
  "operator_nick": "小红",
  "times": 1
}
```

### 输入状态

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `notice` |
| `notice_type` | string | `notify` |
| `sub_type` | string | `input_status` |
| `user_id` | number | 用户QQ号 |
| `group_id` | number | 群号（群聊时） |
| `status_text` | string | 状态文本 |
| `event_type` | number | 事件类型 |

**示例：**

```json
{
  "time": 1718000025,
  "self_id": 123456789,
  "post_type": "notice",
  "notice_type": "notify",
  "sub_type": "input_status",
  "user_id": 777888999,
  "status_text": "正在输入...",
  "event_type": 1
}
```

---

## 请求事件

请求事件的 `post_type` 为 `request`。

### 加好友请求

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `request` |
| `request_type` | string | `friend` |
| `user_id` | number | 发送请求的QQ号 |
| `comment` | string | 验证信息 |
| `flag` | string | 请求flag |

**示例：**

```json
{
  "time": 1718000030,
  "self_id": 123456789,
  "post_type": "request",
  "request_type": "friend",
  "user_id": 456789012,
  "comment": "我是机器人粉丝",
  "flag": "request_flag_1"
}
```

### 加群请求/邀请

**事件数据：**

| 字段名 | 类型 | 可能的值 | 说明 |
|--------|------|----------|------|
| `time` | number | - | 事件发生的时间戳 |
| `self_id` | number | - | 收到事件的机器人QQ号 |
| `post_type` | string | `request` | 上报类型 |
| `request_type` | string | `group` | 请求类型 |
| `sub_type` | string | `add`、`invite` | 请求子类型 |
| `group_id` | number | - | 群号 |
| `user_id` | number | - | 发送请求的QQ号 |
| `comment` | string | - | 验证信息 |
| `flag` | string | - | 请求flag |

**示例：**

```json
{
  "time": 1718000031,
  "self_id": 123456789,
  "post_type": "request",
  "request_type": "group",
  "sub_type": "add",
  "group_id": 987654321,
  "user_id": 456789013,
  "comment": "想加入群聊",
  "flag": "request_flag_2"
}
```

---

## 元事件

元事件的 `post_type` 为 `meta_event`。

### 生命周期

**事件数据：**

| 字段名 | 类型 | 可能的值 | 说明 |
|--------|------|----------|------|
| `time` | number | - | 事件发生的时间戳 |
| `self_id` | number | - | 收到事件的机器人QQ号 |
| `post_type` | string | `meta_event` | 上报类型 |
| `meta_event_type` | string | `lifecycle` | 元事件类型 |
| `sub_type` | string | `connect` | 事件子类型（NapCat仅支持connect） |

**示例：**

```json
{
  "time": 1718000040,
  "self_id": 123456789,
  "post_type": "meta_event",
  "meta_event_type": "lifecycle",
  "sub_type": "connect"
}
```

### 心跳

**事件数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 事件发生的时间戳 |
| `self_id` | number | 收到事件的机器人QQ号 |
| `post_type` | string | `meta_event` |
| `meta_event_type` | string | `heartbeat` |
| `status` | object | 状态信息 |
| `interval` | number | 到下次心跳的间隔（毫秒） |

**status 字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `online` | boolean | 当前QQ在线状态 |
| `good` | boolean | 状态符合预期 |

**示例：**

```json
{
  "time": 1718000041,
  "self_id": 123456789,
  "post_type": "meta_event",
  "meta_event_type": "heartbeat",
  "status": {
    "online": true,
    "good": true
  },
  "interval": 15000
}
```

---

## 注意事项

1. **时间戳单位**：`time` 字段为秒级时间戳
2. **字段存在性**：某些字段可能因情况不同而不存在，使用时需要判断
3. **sender 字段**：sender中的各字段是尽最大努力提供的，不保证完全准确
4. **快速操作**：部分事件支持快速操作，可通过 `.handle_quick_operation` API 实现
5. **事件过滤**：建议根据 `post_type`、`message_type`、`notice_type` 等字段进行事件分类处理
