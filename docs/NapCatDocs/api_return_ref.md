# API 返回值完整参考

本文档详细说明 NapCat 所有 API 的返回值结构。

## 返回值基础说明

### 标准响应格式

所有 API 调用都会返回一个标准的 JSON 响应：

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    // API 返回的具体数据
  },
  "message": "",
  "wording": ""
}
```

**响应字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `status` | string | 状态：`ok` 表示成功，`async` 表示异步调用，`failed` 表示失败 |
| `retcode` | number | 返回码：0 表示成功，非0表示失败 |
| `data` | object | 返回数据，本文档主要说明此字段 |
| `message` | string | 错误信息 |
| `wording` | string | 建议的错误提示 |

### 无返回数据的 API

部分 API 执行成功后没有返回数据，`data` 字段为 `null` 或空对象 `{}`。

---

## 消息相关

### send_private_msg / send_group_msg / send_msg

发送消息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `message_id` | number | 消息ID |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "message_id": 123456
  }
}
```

### get_msg

获取消息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | number | 发送时间 |
| `message_type` | string | 消息类型：`private`、`group` |
| `message_id` | number | 消息ID |
| `real_id` | number | 消息真实ID |
| `sender` | object | 发送人信息 |
| `message` | array | 消息内容（消息段数组） |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "time": 1718000000,
    "message_type": "group",
    "message_id": 123456,
    "real_id": 123456,
    "sender": {
      "user_id": 10001,
      "nickname": "测试"
    },
    "message": [
      {
        "type": "text",
        "data": {
          "text": "你好"
        }
      }
    ]
  }
}
```

### get_forward_msg

获取合并转发消息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `message` | array | 消息内容，全部为node消息段 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "message": [
      {
        "type": "node",
        "data": {
          "user_id": "10001",
          "nickname": "用户A",
          "content": [
            {
              "type": "text",
              "data": {
                "text": "第一条消息"
              }
            }
          ]
        }
      }
    ]
  }
}
```

### send_group_forward_msg / send_private_forward_msg / send_forward_msg

发送合并转发消息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `message_id` | number | 消息ID |
| `res_id` | string | 转发消息ID |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "message_id": 123456,
    "res_id": "abc123def456"
  }
}
```

### get_group_msg_history / get_friend_msg_history

获取历史消息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `messages` | array | 消息列表 |

**messages 数组元素：** 同 `get_msg` 返回的数据结构

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "messages": [
      {
        "time": 1718000000,
        "message_type": "group",
        "message_id": 123456,
        "real_id": 123456,
        "sender": {
          "user_id": 10001,
          "nickname": "测试"
        },
        "message": [
          {
            "type": "text",
            "data": {
              "text": "历史消息"
            }
          }
        ]
      }
    ]
  }
}
```

### delete_msg / mark_msg_as_read / mark_private_msg_as_read / mark_group_msg_as_read / _mark_all_as_read

这些 API 执行成功后无返回数据。

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": null
}
```

### forward_friend_single_msg / forward_group_single_msg

转发单条消息，无返回数据。

### set_msg_emoji_like

设置消息表情回应，无返回数据。

---

## 好友相关

### send_like

发送好友赞，无返回数据。

### get_stranger_info

获取陌生人信息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `user_id` | number | QQ号 |
| `nickname` | string | 昵称 |
| `sex` | string | 性别：`male`、`female`、`unknown` |
| `age` | number | 年龄 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "user_id": 10001,
    "nickname": "小明",
    "sex": "male",
    "age": 18
  }
}
```

### get_friend_list

获取好友列表。

**返回数据：** 数组，每个元素包含：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `user_id` | number | QQ号 |
| `nickname` | string | 昵称 |
| `remark` | string | 备注名 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": [
    {
      "user_id": 10001,
      "nickname": "小明",
      "remark": "好友A"
    },
    {
      "user_id": 10002,
      "nickname": "小红",
      "remark": "好友B"
    }
  ]
}
```

### get_friends_with_category

获取分类好友列表。

**返回数据：** 数组，每个元素包含：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `categoryId` | number | 分类ID |
| `categorySortId` | number | 分类排序ID |
| `categoryName` | string | 分类名称 |
| `categoryMbCount` | number | 分类内好友总数 |
| `onlineCount` | number | 在线数量 |
| `buddyList` | array | 好友列表 |

**buddyList 数组元素：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `user_id` | number | QQ号 |
| `nickname` | string | 昵称 |
| `remark` | string | 备注 |
| `qid` | string | QQ ID |
| `longNick` | string | 个性签名 |
| `sex` | string | 性别 |
| `level` | number | QQ等级 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": [
    {
      "categoryId": 1,
      "categoryName": "我的好友",
      "categoryMbCount": 10,
      "onlineCount": 5,
      "buddyList": [
        {
          "user_id": 10001,
          "nickname": "小明",
          "remark": "好友A",
          "level": 64
        }
      ]
    }
  ]
}
```

### delete_friend / set_friend_remark / set_friend_add_request / friend_poke

这些 API 执行成功后无返回数据。

---

## 群组相关

### get_group_info

获取群信息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `group_id` | number | 群号 |
| `group_name` | string | 群名称 |
| `member_count` | number | 成员数 |
| `max_member_count` | number | 最大成员数 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "group_id": 123456,
    "group_name": "测试群",
    "member_count": 100,
    "max_member_count": 200
  }
}
```

### get_group_list

获取群列表。

**返回数据：** 数组，每个元素同 `get_group_info` 的返回结构。

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": [
    {
      "group_id": 123456,
      "group_name": "测试群1",
      "member_count": 100,
      "max_member_count": 200
    },
    {
      "group_id": 789012,
      "group_name": "测试群2",
      "member_count": 50,
      "max_member_count": 100
    }
  ]
}
```

### get_group_member_info

获取群成员信息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `group_id` | number | 群号 |
| `user_id` | number | QQ号 |
| `nickname` | string | 昵称 |
| `card` | string | 群名片/备注 |
| `sex` | string | 性别：`male`、`female`、`unknown` |
| `age` | number | 年龄 |
| `area` | string | 地区 |
| `join_time` | number | 加群时间戳 |
| `last_sent_time` | number | 最后发言时间戳 |
| `level` | string | 成员等级 |
| `role` | string | 角色：`owner`、`admin`、`member` |
| `unfriendly` | boolean | 是否不良记录成员 |
| `title` | string | 专属头衔 |
| `title_expire_time` | number | 专属头衔过期时间戳 |
| `card_changeable` | boolean | 是否允许修改群名片 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "group_id": 123456,
    "user_id": 10001,
    "nickname": "小明",
    "card": "管理员",
    "sex": "male",
    "age": 20,
    "role": "admin",
    "title": "活跃成员",
    "level": "10"
  }
}
```

### get_group_member_list

获取群成员列表。

**返回数据：** 数组，每个元素同 `get_group_member_info` 的返回结构。

### get_group_honor_info

获取群荣誉信息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `group_id` | number | 群号 |
| `current_talkative` | object | 当前龙王 |
| `talkative_list` | array | 历史龙王 |
| `performer_list` | array | 群聊之火 |
| `legend_list` | array | 群聊炽焰 |
| `strong_newbie_list` | array | 冒尖小春笋 |
| `emotion_list` | array | 快乐之源 |

**current_talkative 对象：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `user_id` | number | QQ号 |
| `nickname` | string | 昵称 |
| `avatar` | string | 头像URL |
| `day_count` | number | 持续天数 |

**其他 list 数组元素：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `user_id` | number | QQ号 |
| `nickname` | string | 昵称 |
| `avatar` | string | 头像URL |
| `description` | string | 荣誉描述 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "group_id": 123456,
    "current_talkative": {
      "user_id": 10001,
      "nickname": "小明",
      "avatar": "http://...",
      "day_count": 7
    },
    "talkative_list": [],
    "performer_list": []
  }
}
```

### get_essence_msg_list

获取精华消息列表。

**返回数据：** 数组，每个元素包含精华消息信息。

### get_group_at_all_remain

获取@全体成员剩余次数。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `can_at_all` | boolean | 是否可以@全体成员 |
| `remain_at_all_count_for_group` | number | 群内剩余次数 |
| `remain_at_all_count_for_uin` | number | 自己剩余次数 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "can_at_all": true,
    "remain_at_all_count_for_group": 10,
    "remain_at_all_count_for_uin": 5
  }
}
```

### _get_group_notice

获取群公告。

**返回数据：** 数组，包含群公告列表。

### get_group_system_msg

获取群系统消息。

**返回数据：** 包含加群请求、邀请等系统消息。

### get_group_ignore_add_request

获取群添加请求忽略列表。

**返回数据：** 数组，包含被忽略的群添加请求。

### get_group_shut_list

获取群禁言列表。

**返回数据：** 数组，包含被禁言的群成员信息。

### set_group_kick / set_group_ban / set_group_whole_ban / set_group_admin / set_group_card / set_group_name / set_group_leave / set_group_special_title / set_group_add_request / set_group_portrait / set_essence_msg / delete_essence_msg / send_group_sign / set_group_sign / set_group_remark / group_poke / _send_group_notice / _del_group_notice

这些 API 执行成功后无返回数据。

---

## 文件相关

### get_group_file_system_info

获取群文件系统信息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `file_count` | number | 文件数量 |
| `limit_count` | number | 文件数量限制 |
| `used_space` | number | 已使用空间 |
| `total_space` | number | 总空间 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "file_count": 10,
    "limit_count": 100,
    "used_space": 1048576,
    "total_space": 10737418240
  }
}
```

### get_group_root_files / get_group_files_by_folder

获取群文件列表。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `files` | array | 文件列表 |
| `folders` | array | 文件夹列表 |

**files 数组元素：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `file_id` | string | 文件ID |
| `file_name` | string | 文件名 |
| `busid` | number | 文件类型 |
| `file_size` | number | 文件大小 |
| `upload_time` | number | 上传时间 |
| `uploader` | number | 上传者 |

**folders 数组元素：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `folder_id` | string | 文件夹ID |
| `folder_name` | string | 文件夹名称 |
| `create_time` | number | 创建时间 |
| `creator` | number | 创建者 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "files": [
      {
        "file_id": "abc123",
        "file_name": "document.pdf",
        "busid": 102,
        "file_size": 1048576,
        "upload_time": 1718000000,
        "uploader": 10001
      }
    ],
    "folders": [
      {
        "folder_id": "folder123",
        "folder_name": "资料",
        "create_time": 1718000000,
        "creator": 10001
      }
    ]
  }
}
```

### get_group_file_url

获取群文件下载链接。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `url` | string | 文件下载URL |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "url": "http://example.com/file/download?id=abc123"
  }
}
```

### get_file

获取文件信息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `file` | string | 文件路径或URL |
| `url` | string | 文件URL |
| `file_size` | string | 文件大小 |
| `file_name` | string | 文件名 |
| `base64` | string | Base64编码 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "file": "/path/to/file",
    "url": "http://example.com/file",
    "file_size": "1024",
    "file_name": "document.pdf"
  }
}
```

### download_file

下载文件到缓存目录。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `file` | string | 下载后的文件路径 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "file": "/cache/downloaded_file.pdf"
  }
}
```

### get_private_file_url

获取私聊文件URL。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `url` | string | 文件下载URL |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "url": "http://example.com/private/file/download?id=abc123"
  }
}
```

### upload_group_file / delete_group_file / create_group_file_folder / delete_group_folder / move_group_file / trans_group_file / rename_group_file / upload_private_file

这些 API 执行成功后无返回数据。

---

## 多媒体相关

### get_image

获取图片。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `file` | string | 图片文件路径 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "file": "/path/to/image.jpg"
  }
}
```

### get_record

获取语音。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `file` | string | 转换后的语音文件路径 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "file": "/path/to/record.mp3"
  }
}
```

### can_send_image / can_send_record

检查是否可以发送图片/语音。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `yes` | boolean | 是否可以发送 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "yes": true
  }
}
```

### ocr_image / .ocr_image

图片OCR识别。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `texts` | array | 识别结果列表 |
| `language` | string | 语言 |

**texts 数组元素：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `text` | string | 识别文字 |
| `confidence` | number | 置信度 |
| `coordinates` | array | 坐标 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "texts": [
      {
        "text": "识别的文字",
        "confidence": 98,
        "coordinates": [0, 0, 100, 50]
      }
    ],
    "language": "zh-CN"
  }
}
```

---

## 账号相关

### get_login_info

获取登录号信息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `user_id` | number | QQ号 |
| `nickname` | string | QQ昵称 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "user_id": 123456789,
    "nickname": "我的QQ"
  }
}
```

### get_status

获取运行状态。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `online` | boolean | 当前QQ在线状态 |
| `good` | boolean | 状态符合预期 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "online": true,
    "good": true
  }
}
```

### get_version_info

获取版本信息。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `app_name` | string | 应用标识 |
| `app_version` | string | 应用版本 |
| `protocol_version` | string | OneBot标准版本 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "app_name": "NapCat",
    "app_version": "2.0.0",
    "protocol_version": "v11"
  }
}
```

### get_online_clients

获取在线客户端列表。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `clients` | array | 客户端列表 |

**clients 数组元素：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `app_id` | number | 客户端ID |
| `device_name` | string | 设备名称 |
| `device_kind` | string | 设备类型 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "clients": [
      {
        "app_id": 1,
        "device_name": "Android",
        "device_kind": "phone"
      }
    ]
  }
}
```

### get_profile_like

获取点赞列表。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `total_count` | number | 总点赞数 |
| `new_count` | number | 新点赞数 |
| `userInfos` | array | 点赞用户信息列表 |

**userInfos 数组元素：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `uid` | string | QQ号 |
| `nick` | string | 昵称 |
| `count` | number | 点赞次数 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "total_count": 100,
    "new_count": 5,
    "userInfos": [
      {
        "uid": "10001",
        "nick": "小明",
        "count": 3
      }
    ]
  }
}
```

### get_cookies

获取Cookies。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `cookies` | string | Cookies字符串 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "cookies": "uin=123456; skey=abc123"
  }
}
```

### get_csrf_token

获取CSRF Token。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `token` | number | CSRF Token |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "token": 123456789
  }
}
```

### get_credentials

获取QQ相关接口凭证。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `cookies` | string | Cookies字符串 |
| `csrf_token` | number | CSRF Token |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "cookies": "uin=123456; skey=abc123",
    "csrf_token": 123456789
  }
}
```

### fetch_emoji_like

获取表情回应列表。

**返回数据：** 数组，包含表情回应信息。

### nc_get_user_status

获取用户状态。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `status` | number | 在线状态码 |
| `ext_status` | number | 扩展状态码 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "status": 10,
    "ext_status": 0
  }
}
```

### set_qq_profile / set_qq_avatar / set_self_longnick / set_online_status / _get_model_show / _set_model_show / set_input_status / clean_cache

这些 API 执行成功后无返回数据。

---

## 其他功能

### get_recent_contact

获取最近联系人。

**返回数据：** 数组，每个元素包含：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `lastestMsg` | object | 最后一条消息 |
| `peerUin` | number | QQ号/群号 |
| `remark` | string | 备注 |
| `msgTime` | string | 消息时间 |
| `chatType` | number | 聊天类型 |
| `msgId` | string | 消息ID |
| `sendNickName` | string | 发送者昵称 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": [
    {
      "peerUin": 10001,
      "remark": "小明",
      "msgTime": "1718000000",
      "chatType": 1,
      "sendNickName": "小明"
    }
  ]
}
```

### ArkSharePeer

获取推荐好友/群聊卡片。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `errCode` | number | 错误码 |
| `errMsg` | string | 错误信息 |
| `arkJson` | string | 卡片JSON |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "errCode": 0,
    "errMsg": "",
    "arkJson": "{...}"
  }
}
```

### ArkShareGroup

获取推荐群聊卡片。

**返回数据：** 卡片JSON字符串

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": "{...}"
}
```

### get_robot_uin_range

获取机器人QQ号范围。

**返回数据：** 数组，每个元素包含：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `minUin` | number | 最小QQ号 |
| `maxUin` | number | 最大QQ号 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": [
    {
      "minUin": 3000000000,
      "maxUin": 3999999999
    }
  ]
}
```

### translate_en2zh

英译中。

**返回数据：** 数组，包含翻译后的中文字符串。

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": ["你好", "世界"]
}
```

### get_collection_list

获取收藏列表。

**返回数据：** 数组，包含收藏信息。

### fetch_custom_face

获取收藏表情。

**返回数据：** 数组，包含表情URL列表。

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": [
    "http://example.com/face1.png",
    "http://example.com/face2.png"
  ]
}
```

### check_url_safely

检查链接安全性。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `level` | number | 安全等级 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "level": 1
  }
}
```

### nc_get_packet_status

获取PacketServer状态。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `status` | string | 状态 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "status": "connected"
  }
}
```

### nc_get_rkey

获取Rkey。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `rkey` | string | Rkey值 |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "rkey": "abc123def456"
  }
}
```

### create_collection / send_poke / get_mini_app_ark / .handle_quick_operation

这些 API 的返回数据视具体情况而定。

---

## AI相关

### get_ai_record

AI文字转语音。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `data` | string | 语音URL |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "data": "http://example.com/ai_voice.mp3"
  }
}
```

### get_ai_characters

获取AI语音角色列表。

**返回数据：** 数组，每个元素包含：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `type` | string | AI分类 |
| `characters` | array | AI角色列表 |

**characters 数组元素：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `character_id` | string | AI角色编号 |
| `character_name` | string | AI角色名称 |
| `preview_url` | string | 预览URL |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": [
    {
      "type": "推荐",
      "characters": [
        {
          "character_id": "1001",
          "character_name": "甜美女声",
          "preview_url": "http://example.com/preview.mp3"
        }
      ]
    }
  ]
}
```

### send_group_ai_record

群聊发送AI语音。

**返回数据：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `message_id` | string | 消息ID |

**示例：**

```json
{
  "status": "ok",
  "retcode": 0,
  "data": {
    "message_id": "123456"
  }
}
```

---

## 注意事项

1. **空返回值**：部分API成功执行后`data`字段为`null`或`{}`，表示无返回数据
2. **异步调用**：异步调用的API返回`status`为`async`
3. **错误处理**：当`retcode`非0时，表示API调用失败，可通过`message`和`wording`字段获取错误信息
4. **字段存在性**：某些字段可能因情况不同而不存在，使用时需要做空值判断
5. **数据类型**：虽然文档标注了类型，但实际使用时number类型可能以string形式返回，需要兼容处理
