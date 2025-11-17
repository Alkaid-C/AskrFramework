# API 接口完整参考

本文档详细说明 NapCat 支持的所有 API 接口及其参数。

## API 调用说明

### 基本格式

API 调用需要指定 `action`（要执行的操作）和相应的参数。

### 特殊调用方式

所有 API 都支持以下特殊调用方式：

- **异步调用**：在 action 后添加 `_async` 后缀（如 `send_msg_async`），调用后立即返回，不等待执行完成
- **限速调用**：在 action 后添加 `_rate_limited` 后缀（如 `send_msg_rate_limited`），调用将排队执行，避免频率过快

### message 类型参数

参数类型为 `message` 的字段可以接受：
- 字符串（CQ码格式）
- 消息段数组
- 单个消息段对象

---

## 消息相关

### send_private_msg - 发送私聊消息

发送私聊消息。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `user_id` | number | 是 | - | 对方QQ号 |
| `message` | message | 是 | - | 要发送的内容 |
| `auto_escape` | boolean | 否 | false | 消息内容是否作为纯文本发送 |

### send_group_msg - 发送群消息

发送群消息。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_id` | number | 是 | - | 群号 |
| `message` | message | 是 | - | 要发送的内容 |
| `auto_escape` | boolean | 否 | false | 消息内容是否作为纯文本发送 |

### send_msg - 发送消息

发送消息（自动判断类型）。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `message_type` | string | 否 | - | 消息类型：`private`、`group`，不传入则根据其他参数判断 |
| `user_id` | number | 否 | - | 对方QQ号（私聊时需要） |
| `group_id` | number | 否 | - | 群号（群聊时需要） |
| `message` | message | 是 | - | 要发送的内容 |
| `auto_escape` | boolean | 否 | false | 消息内容是否作为纯文本发送 |

### delete_msg - 撤回消息

撤回消息。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `message_id` | number | 是 | 消息ID |

### get_msg - 获取消息

获取消息详情。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `message_id` | number | 是 | 消息ID |

### get_forward_msg - 获取合并转发消息

获取合并转发消息内容。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `id` | string | 是 | 合并转发ID |

### send_group_forward_msg - 发送合并转发（群聊）

发送合并转发消息到群聊。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `messages` | array | 是 | node消息段数组 |

### send_private_forward_msg - 发送合并转发（私聊）

发送合并转发消息到私聊。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user_id` | number | 是 | QQ号 |
| `messages` | array | 是 | node消息段数组 |

### send_forward_msg - 发送合并转发

发送合并转发消息（自动判断类型）。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `message_type` | string | 否 | 消息类型：`private`、`group` |
| `user_id` | number | 否 | QQ号（私聊时需要） |
| `group_id` | number | 否 | 群号（群聊时需要） |
| `messages` | array | 是 | node消息段数组 |

### mark_msg_as_read - 标记消息已读

标记消息为已读。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `message_id` | number | 是 | 消息ID |

### mark_private_msg_as_read - 标记私聊消息已读

标记私聊消息为已读。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user_id` | number | 是 | QQ号 |

### mark_group_msg_as_read - 标记群聊消息已读

标记群聊消息为已读。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |

### _mark_all_as_read - 标记所有消息已读

标记所有消息为已读。

**参数：** 无

### get_group_msg_history - 获取群消息历史记录

获取群聊历史消息。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `message_seq` | number | 否 | 起始消息序号 |
| `count` | number | 否 | 获取数量 |

### get_friend_msg_history - 获取私聊消息历史记录

获取私聊历史消息。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `user_id` | string | 是 | - | QQ号 |
| `message_seq` | string | 否 | '0' | 起始消息序号 |
| `count` | number | 否 | 20 | 获取数量 |
| `reverseOrder` | boolean | 否 | false | 是否倒序 |

### forward_friend_single_msg - 转发单条消息到私聊

转发单条消息到私聊。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user_id` | number | 是 | 目标QQ号 |
| `message_id` | number | 是 | 消息ID |

### forward_group_single_msg - 转发单条消息到群聊

转发单条消息到群聊。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 目标群号 |
| `message_id` | number | 是 | 消息ID |

### set_msg_emoji_like - 设置消息表情回应

设置消息的表情回应。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `message_id` | number | 是 | 消息ID |
| `emoji_id` | string | 是 | 表情ID |

---

## 好友相关

### send_like - 发送好友赞

给好友点赞。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `user_id` | number | 是 | - | 对方QQ号 |
| `times` | number | 否 | 1 | 点赞次数，每天最多10次 |

### get_stranger_info - 获取陌生人信息

获取陌生人信息。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `user_id` | number | 是 | - | QQ号 |
| `no_cache` | boolean | 否 | false | 是否不使用缓存 |

### get_friend_list - 获取好友列表

获取好友列表。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `no_cache` | boolean | 否 | false | 是否不使用缓存 |

### get_friends_with_category - 获取分类好友列表

获取带分类的好友列表。

**参数：** 无

### delete_friend - 删除好友

删除好友。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user_id` | number | 是 | QQ号 |

### set_friend_remark - 设置好友备注

设置好友备注名。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user_id` | number | 是 | QQ号 |
| `remark` | string | 是 | 备注名 |

### set_friend_add_request - 处理加好友请求

处理加好友请求。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `flag` | string | 是 | - | 请求flag |
| `approve` | boolean | 否 | true | 是否同意 |
| `remark` | string | 否 | - | 好友备注 |

### friend_poke - 私聊戳一戳

发送私聊戳一戳。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user_id` | number | 是 | 对方QQ号 |

---

## 群组相关

### set_group_kick - 群组踢人

踢出群成员。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_id` | number | 是 | - | 群号 |
| `user_id` | number | 是 | - | 要踢的QQ号 |
| `reject_add_request` | boolean | 否 | false | 是否拒绝此人的加群请求 |

### set_group_ban - 群组单人禁言

禁言群成员。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_id` | number | 是 | - | 群号 |
| `user_id` | number | 是 | - | 要禁言的QQ号 |
| `duration` | number | 否 | 1800 | 禁言时长（秒），0表示取消禁言 |

### set_group_whole_ban - 群组全员禁言

设置全员禁言。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_id` | number | 是 | - | 群号 |
| `enable` | boolean | 否 | true | 是否禁言 |

### set_group_admin - 群组设置管理员

设置群管理员。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_id` | number | 是 | - | 群号 |
| `user_id` | number | 是 | - | QQ号 |
| `enable` | boolean | 否 | true | true为设置，false为取消 |

### set_group_card - 设置群名片

设置群成员名片。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_id` | number | 是 | - | 群号 |
| `user_id` | number | 是 | - | QQ号 |
| `card` | string | 否 | - | 群名片，空字符串表示删除 |

### set_group_name - 设置群名

设置群名称。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `group_name` | string | 是 | 新群名 |

### set_group_leave - 退出群组

退出群聊。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_id` | number | 是 | - | 群号 |
| `is_dismiss` | boolean | 否 | false | 是否解散（仅群主可用） |

### set_group_special_title - 设置群组专属头衔

设置群成员专属头衔。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_id` | number | 是 | - | 群号 |
| `user_id` | number | 是 | - | QQ号 |
| `special_title` | string | 否 | - | 专属头衔，空字符串表示删除 |
| `duration` | number | 否 | -1 | 有效期（秒），-1表示永久 |

### get_group_info - 获取群信息

获取群信息。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_id` | number | 是 | - | 群号 |
| `no_cache` | boolean | 否 | false | 是否不使用缓存 |

### get_group_list - 获取群列表

获取群列表。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `no_cache` | boolean | 否 | false | 是否不使用缓存 |

### get_group_info_ex - 获取群信息扩展

获取群扩展信息。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |

### get_group_member_info - 获取群成员信息

获取群成员信息。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_id` | number | 是 | - | 群号 |
| `user_id` | number | 是 | - | QQ号 |
| `no_cache` | boolean | 否 | false | 是否不使用缓存 |

### get_group_member_list - 获取群成员列表

获取群成员列表。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_id` | number | 是 | - | 群号 |
| `no_cache` | boolean | 否 | false | 是否不使用缓存 |

### get_group_honor_info - 获取群荣誉信息

获取群荣誉信息。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `type` | string | 是 | 荣誉类型：`talkative`、`performer`、`legend`、`strong_newbie`、`emotion`、`all` |

### set_group_add_request - 处理加群请求

处理加群请求/邀请。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `flag` | string | 是 | - | 请求flag |
| `sub_type` 或 `type` | string | 是 | - | 请求类型：`add`、`invite` |
| `approve` | boolean | 否 | true | 是否同意 |
| `reason` | string | 否 | - | 拒绝理由 |

### set_group_portrait - 设置群头像

设置群头像。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `file` | string | 是 | 图片路径或URL |
| `cache` | number | 否 | 是否使用缓存 |

### get_essence_msg_list - 获取精华消息列表

获取群精华消息列表。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |

### set_essence_msg - 设置精华消息

设置精华消息。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `message_id` | number | 是 | 消息ID |

### delete_essence_msg - 删除精华消息

移出精华消息。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `message_id` | number | 是 | 消息ID |

### get_group_at_all_remain - 获取群@全体成员剩余次数

获取群@全体成员剩余次数。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |

### _send_group_notice - 发送群公告

发送群公告。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `content` | string | 是 | 公告内容 |

### _get_group_notice - 获取群公告

获取群公告。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |

### _del_group_notice - 删除群公告

删除群公告。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `notice_id` | string | 是 | 公告ID |

### get_group_system_msg - 获取群系统消息

获取群系统消息。

**参数：** 无

### get_group_ignore_add_request - 获取群添加请求忽略列表

获取被忽略的群添加请求。

**参数：** 无

### get_group_shut_list - 获取群禁言列表

获取群禁言用户列表。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |

### set_group_remark - 设置群备注

设置群备注。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `remark` | string | 是 | 群备注 |

### send_group_sign - 群打卡

群打卡/签到。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |

### set_group_sign - 群签到

群签到。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | string | 是 | 群号 |

### group_poke - 群聊戳一戳

发送群聊戳一戳。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `user_id` | number | 是 | 对方QQ号 |

---

## 文件相关

### upload_group_file - 上传群文件

上传文件到群文件。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `file` | string | 是 | 本地文件路径 |
| `name` | string | 是 | 文件名称 |
| `folder` | string | 否 | 父目录ID |

### delete_group_file - 删除群文件

删除群文件。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `file_id` | string | 是 | 文件ID |
| `busid` | number | 是 | 文件类型 |

### create_group_file_folder - 创建群文件文件夹

创建群文件文件夹。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `name` | string | 是 | 文件夹名称 |
| `parent_id` | string | 否 | 父目录ID |

### delete_group_folder - 删除群文件文件夹

删除群文件文件夹。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `folder_id` | string | 是 | 文件夹ID |

### get_group_file_system_info - 获取群文件系统信息

获取群文件系统信息。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |

### get_group_root_files - 获取群根目录文件列表

获取群根目录文件列表。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |

### get_group_files_by_folder - 获取群子目录文件列表

获取群子目录文件列表。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `folder_id` | string | 是 | 文件夹ID |

### get_group_file_url - 获取群文件链接

获取群文件下载链接。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `file_id` | string | 是 | 文件ID |
| `busid` | number | 是 | 文件类型 |

### move_group_file - 移动群文件

移动群文件到指定目录。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `file_id` | string | 是 | 文件ID |
| `folder_id` | string | 是 | 目标文件夹ID |
| `busid` | number | 是 | 文件类型 |

### trans_group_file - 转发群文件

转发群文件到其他群。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 源群号 |
| `file_id` | string | 是 | 文件ID |
| `busid` | number | 是 | 文件类型 |
| `target_group_id` | number | 是 | 目标群号 |

### rename_group_file - 重命名群文件

重命名群文件。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `file_id` | string | 是 | 文件ID |
| `busid` | number | 是 | 文件类型 |
| `parent_directory` | string | 是 | 父目录ID |
| `new_name` | string | 是 | 新文件名 |

### upload_private_file - 上传私聊文件

上传文件到私聊。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user_id` | number | 是 | QQ号 |
| `file` | string | 是 | 本地文件路径 |
| `name` | string | 是 | 文件名称 |

### get_private_file_url - 获取私聊文件URL

获取私聊文件下载链接。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user_id` | number | 是 | QQ号 |
| `file_id` | string | 是 | 文件ID |

### get_file - 获取文件信息

获取文件信息。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file_id` | string | 是 | 文件ID |

### download_file - 下载文件到缓存目录

下载文件到缓存目录。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `url` | string | 是 | 文件URL |
| `thread_count` | number | 否 | 下载线程数 |
| `headers` | array | 否 | 自定义请求头 |

---

## 多媒体相关

### get_image - 获取图片

获取图片信息。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file` | string | 是 | 图片文件名 |

### get_record - 获取语音

获取语音文件。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file` | string | 是 | 语音文件名 |
| `out_format` | string | 是 | 输出格式：`mp3`、`amr`、`wma`、`m4a`、`spx`、`ogg`、`wav`、`flac` |

### can_send_image - 检查是否可以发送图片

检查是否可以发送图片。

**参数：** 无

### can_send_record - 检查是否可以发送语音

检查是否可以发送语音。

**参数：** 无

### ocr_image - 图片OCR识别

图片OCR文字识别。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `image` | string | 是 | 图片ID |

### .ocr_image - 图片OCR识别（增强版）

图片OCR文字识别（增强版）。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `image` | string | 是 | 图片ID |

---

## 账号相关

### get_login_info - 获取登录号信息

获取登录号信息。

**参数：** 无

### get_status - 获取运行状态

获取运行状态。

**参数：** 无

### get_version_info - 获取版本信息

获取版本信息。

**参数：** 无

### set_qq_profile - 设置登录号资料

设置登录号资料。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `nickname` | string | 否 | 昵称 |
| `company` | string | 否 | 公司 |
| `email` | string | 否 | 邮箱 |
| `college` | string | 否 | 学校 |
| `personal_note` | string | 否 | 个人说明 |

### set_qq_avatar - 设置QQ头像

设置QQ头像。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file` | string | 是 | 图片路径或URL |

### set_self_longnick - 设置个性签名

设置个性签名。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `longNick` | string | 是 | 个性签名内容 |

### set_online_status - 设置在线状态

设置在线状态。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `status` | number | 是 | 状态码 |
| `ext_status` | number | 是 | 扩展状态码 |
| `battery_status` | number | 是 | 电量 |

### get_online_clients - 获取在线客户端列表

获取当前账号在线客户端列表。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `no_cache` | boolean | 否 | false | 是否不使用缓存 |

### _get_model_show - 获取在线机型

获取在线机型。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `model` | string | 是 | 机型名称 |

### _set_model_show - 设置在线机型

设置在线机型。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `model` | string | 是 | 机型名称 |
| `model_show` | string | 否 | 显示名称 |

### get_profile_like - 获取点赞列表

获取自身点赞列表。

**参数：** 无

### set_input_status - 设置输入状态

设置输入状态。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user_id` | number | 是 | QQ号 |
| `event_type` | number | 是 | 事件类型 |

### fetch_emoji_like - 获取表情回应列表

获取表情回应列表。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `message_id` | number | 是 | 消息ID |

### nc_get_user_status - 获取用户状态

获取陌生人在线状态。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user_id` | number | 是 | QQ号 |

---

## 其他功能

### get_cookies - 获取Cookies

获取Cookies。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `domain` | string | 否 | 需要获取cookies的域名 |

### get_csrf_token - 获取CSRF Token

获取CSRF Token。

**参数：** 无

### get_credentials - 获取QQ相关接口凭证

获取QQ相关接口凭证（Cookies + CSRF Token）。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `domain` | string | 否 | 需要获取cookies的域名 |

### clean_cache - 清理缓存

清理缓存。

**参数：** 无

### get_recent_contact - 获取最近联系人

获取最近联系人列表。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `count` | number | 否 | 10 | 获取数量 |

### ArkSharePeer - 获取推荐好友/群聊卡片

获取推荐好友或群聊的卡片。

**参数（好友）：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user_id` | string | 是 | 对方QQ号 |
| `phoneNumber` | string | 否 | 对方手机号 |

**参数（群聊）：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | string | 是 | 群号 |

### ArkShareGroup - 获取推荐群聊卡片

获取推荐群聊卡片。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | string | 是 | 群号 |

### get_robot_uin_range - 获取机器人QQ号范围

获取机器人账号范围。

**参数：** 无

### translate_en2zh - 英译中

英文翻译成中文。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `words` | array | 是 | 英文单词数组 |

### create_collection - 创建收藏

创建收藏。

**参数：** 待补充

### get_collection_list - 获取收藏列表

获取收藏列表。

**参数：** 无

### fetch_custom_face - 获取收藏表情

获取收藏表情列表。

**参数：**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `count` | number | 否 | 48 | 获取数量 |

### check_url_safely - 检查链接安全性

检查URL安全性。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `url` | string | 是 | 要检查的URL |

### send_poke - 发送戳一戳

发送群聊/私聊戳一戳（自动判断）。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 否 | 群号（群聊时需要） |
| `user_id` | number | 是 | 对方QQ号 |

### get_mini_app_ark - 签名小程序卡片

获取签名的小程序卡片。

**参数：** 待补充

### nc_get_packet_status - 获取PacketServer状态

获取PacketServer状态。

**参数：** 无

### nc_get_rkey - 获取Rkey

获取Rkey。

**参数：** 无

### .handle_quick_operation - 对事件执行快速操作

对事件执行快速操作（隐藏API）。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `context` | object | 是 | 事件数据对象 |
| `operation` | object | 是 | 快速操作对象 |

---

## AI相关

### get_ai_record - AI文字转语音

AI文字转语音。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `character` | string | 是 | AI角色编号 |
| `group_id` | number | 是 | 群号 |
| `text` | string | 是 | 要转换的文字 |

### get_ai_characters - 获取AI语音角色列表

获取AI语音角色列表。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `group_id` | number | 是 | 群号 |
| `chat_type` | number | 否 | 聊天类型 |

### send_group_ai_record - 群聊发送AI语音

群聊发送AI语音。

**参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `character` | string | 是 | AI角色编号 |
| `group_id` | number | 是 | 群号 |
| `text` | string | 是 | 要转换的文字 |

---

## 注意事项

1. **参数类型**：number类型的参数通常也可以接受string类型
2. **必填判断**：未标注必填的参数均为可选参数
3. **返回值**：所有API的返回值详见 [API返回值参考](api_return_ref.md)
4. **异步调用**：耗时操作建议使用异步调用（添加`_async`后缀）
5. **限速调用**：发送消息类API建议使用限速调用（添加`_rate_limited`后缀）避免被封号
6. **隐藏API**：以`.`开头的API为隐藏API，不建议一般用户使用
