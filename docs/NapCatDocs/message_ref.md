# 消息段完整参考

本文档详细说明 NapCat 支持的所有消息段类型及其数据结构。

## 消息格式说明

消息使用数组格式表示，每条消息由若干消息段（Segment）组成。每个消息段的基本结构为：

```json
{
  "type": "消息段类型",
  "data": {
    // 该类型特定的数据字段
  }
}
```

**示例消息：**

```json
[
  {
    "type": "text",
    "data": {
      "text": "你好"
    }
  },
  {
    "type": "image",
    "data": {
      "file": "https://example.com/image.jpg"
    }
  }
]
```

## 消息段类型

### 文本类消息段

#### text - 纯文本

用于发送纯文本内容。

**发送参数：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `text` | string | 纯文本内容 |

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `text` | string | 纯文本内容 |

**示例：**

```json
{
  "type": "text",
  "data": {
    "text": "这是一段纯文本"
  }
}
```

#### at - @某人

用于在消息中@特定用户或全体成员。

**发送参数：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `qq` | string | 要@的QQ号，使用 "all" 表示@全体成员 |

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `qq` | string | 被@的QQ号或 "all" |

**示例：**

```json
{
  "type": "at",
  "data": {
    "qq": "10001000"
  }
}
```

```json
{
  "type": "at",
  "data": {
    "qq": "all"
  }
}
```

#### reply - 回复

用于回复特定消息。

**发送参数：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | string | 被回复消息的ID |

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | string | 被回复消息的ID |

**示例：**

```json
{
  "type": "reply",
  "data": {
    "id": "123456"
  }
}
```

---

### 表情类消息段

#### face - QQ表情

用于发送QQ内置表情。

**发送参数：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | string | QQ表情ID |

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | string | QQ表情ID |

**示例：**

```json
{
  "type": "face",
  "data": {
    "id": "123"
  }
}
```

#### mface - 商城表情

用于发送QQ商城表情。接收时通常转换为image类型，并包含额外字段。

**发送参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `emoji_id` | string | 是 | 表情ID |
| `emoji_package_id` | string | 是 | 表情包ID |
| `key` | string | 否 | 表情key |
| `summary` | string | 否 | 表情名称 |

**接收时：** 通常转换为image类型，data中包含：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `file` | string | 图片文件标识 |
| `url` | string | 图片URL |
| `emoji_id` | string | 表情ID |
| `emoji_package_id` | string | 表情包ID |
| `key` | string | 表情key |

**发送示例：**

```json
{
  "type": "mface",
  "data": {
    "emoji_id": "123",
    "emoji_package_id": "456",
    "summary": "可爱表情"
  }
}
```

#### rps - 石头剪刀布

用于发送石头剪刀布魔法表情。

**发送参数：** 无需参数

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `result` | string | 结果(1-3，分别代表石头、剪刀、布) |

**示例：**

```json
{
  "type": "rps",
  "data": {}
}
```

#### dice - 骰子

用于发送骰子魔法表情。

**发送参数：** 无需参数

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `result` | string | 骰子点数(1-6) |

**示例：**

```json
{
  "type": "dice",
  "data": {}
}
```

#### shake - 窗口抖动

窗口抖动消息。仅接收，不支持发送。

**接收字段：** 无特殊字段

**示例：**

```json
{
  "type": "shake",
  "data": {}
}
```

#### poke - 戳一戳

用于发送戳一戳消息。

**发送参数：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `type` | string | 戳一戳类型 |
| `id` | string | 戳一戳ID |

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `type` | string | 戳一戳类型 |
| `id` | string | 戳一戳ID |
| `name` | string | 表情名 |

**示例：**

```json
{
  "type": "poke",
  "data": {
    "type": "126",
    "id": "2003"
  }
}
```

---

### 多媒体类消息段

#### image - 图片

用于发送图片。

**发送参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file` | string | 是 | 图片文件路径、URL或Base64编码 |
| `name` | string | 否 | 图片文件名 |
| `summary` | string | 否 | 图片描述 |
| `sub_type` | number | 否 | 图片子类型 |
| `type` | string | 否 | 图片类型，`flash` 表示闪照 |
| `cache` | boolean | 否 | 是否使用缓存，默认true |
| `proxy` | boolean | 否 | 是否通过代理下载，默认true |
| `timeout` | number | 否 | 下载超时时间（秒） |

**file参数支持的格式：**
- 绝对路径：`file:///C:\\Users\\Pictures\\1.png`
- 网络URL：`http://example.com/image.jpg`
- Base64编码：`base64://iVBORw0KGgoAAAANSUhEUgAA...`

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `file` | string | 图片文件名 |
| `url` | string | 图片URL |
| `file_size` | number | 文件大小（字节） |
| `summary` | string | 图片描述 |
| `sub_type` | number | 图片子类型 |
| `type` | string | 图片类型 |

**示例：**

```json
{
  "type": "image",
  "data": {
    "file": "http://example.com/image.jpg"
  }
}
```

```json
{
  "type": "image",
  "data": {
    "file": "file:///C:\\Users\\Pictures\\photo.png",
    "summary": "我的照片"
  }
}
```

#### record - 语音

用于发送语音消息。

**发送参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file` | string | 是 | 语音文件路径、URL或Base64编码 |
| `name` | string | 否 | 语音文件名 |
| `magic` | boolean | 否 | 是否变声，默认false |
| `cache` | boolean | 否 | 是否使用缓存，默认true |
| `proxy` | boolean | 否 | 是否通过代理下载，默认true |
| `timeout` | number | 否 | 下载超时时间（秒） |

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `file` | string | 语音文件标识 |
| `url` | string | 语音URL |
| `file_size` | number | 文件大小（字节） |
| `path` | string | 文件路径 |

**示例：**

```json
{
  "type": "record",
  "data": {
    "file": "http://example.com/audio.mp3"
  }
}
```

#### video - 视频

用于发送视频。

**发送参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file` | string | 是 | 视频文件路径、URL或Base64编码 |
| `name` | string | 否 | 视频文件名 |
| `thumb` | string | 否 | 视频缩略图 |
| `cache` | boolean | 否 | 是否使用缓存，默认true |
| `proxy` | boolean | 否 | 是否通过代理下载，默认true |
| `timeout` | number | 否 | 下载超时时间（秒） |

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `file` | string | 视频文件标识 |
| `url` | string | 视频URL |
| `file_size` | number | 文件大小（字节） |
| `path` | string | 文件路径 |

**示例：**

```json
{
  "type": "video",
  "data": {
    "file": "http://example.com/video.mp4"
  }
}
```

#### file - 文件

用于发送文件。

**发送参数：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file` | string | 是 | 文件路径、URL或Base64编码 |
| `name` | string | 否 | 文件名 |

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `file` | string | 文件名 |
| `file_id` | string | 文件ID |
| `file_size` | number | 文件大小（字节） |
| `url` | string | 文件URL |
| `path` | string | 文件路径 |

**示例：**

```json
{
  "type": "file",
  "data": {
    "file": "http://example.com/document.pdf",
    "name": "说明文档.pdf"
  }
}
```

---

### 分享与推荐类消息段

#### share - 链接分享

链接分享消息。**仅接收**，不支持发送。接收时以json类型上报。

**接收字段：**

通常包含以下字段（作为json类型消息段接收）：
- `url` - 链接URL
- `title` - 标题
- `content` - 内容描述
- `image` - 图片URL

**示例：**

```json
{
  "type": "json",
  "data": {
    "data": "{\"app\":\"com.tencent.structmsg\",\"desc\":\"\",\"view\":\"share\",\"meta\":{\"detail_1\":{...}}}"
  }
}
```

#### contact - 推荐好友/群

用于推荐好友或群聊。

**推荐好友：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `type` | string | 固定为 "qq" |
| `id` | string | 被推荐人的QQ号 |

**推荐群：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `type` | string | 固定为 "group" |
| `id` | string | 被推荐群的群号 |

**示例：**

```json
{
  "type": "contact",
  "data": {
    "type": "qq",
    "id": "10001000"
  }
}
```

```json
{
  "type": "contact",
  "data": {
    "type": "group",
    "id": "100100"
  }
}
```

#### location - 位置

位置分享消息。**仅接收**，不支持发送。接收时以json类型上报。

**接收字段：**

通常包含以下字段（作为json类型消息段接收）：
- `lat` - 纬度
- `lon` - 经度
- `title` - 位置标题
- `content` - 位置描述

**示例：**

```json
{
  "type": "json",
  "data": {
    "data": "{\"app\":\"com.tencent.map\",\"desc\":\"\",\"view\":\"LocationShare\",\"meta\":{\"Location.Search\":{...}}}"
  }
}
```

#### music - 音乐分享

用于分享音乐。仅支持发送，接收时为json类型。

**平台音乐分享：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `type` | string | 音乐平台：`qq`、`163`、`xm`、`kugou`、`kuwo`、`migu` |
| `id` | string | 歌曲ID |

**自定义音乐分享：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `type` | string | 是 | 固定为 "custom" |
| `url` | string | 是 | 点击后跳转URL |
| `audio` | string | 是 | 音乐URL |
| `title` | string | 是 | 标题 |
| `content` | string | 否 | 内容描述 |
| `image` | string | 否 | 封面图片URL |
| `singer` | string | 否 | 歌手 |

**示例：**

```json
{
  "type": "music",
  "data": {
    "type": "163",
    "id": "28949129"
  }
}
```

```json
{
  "type": "music",
  "data": {
    "type": "custom",
    "url": "http://example.com/music",
    "audio": "http://example.com/audio.mp3",
    "title": "歌曲名称",
    "singer": "歌手名"
  }
}
```

---

### 转发类消息段

#### forward - 合并转发

用于表示合并转发消息。接收时可获取转发ID，需通过API获取具体内容。

**发送参数：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | string | 转发消息ID |

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | string | 合并转发ID |
| `content` | array | 转发的消息内容列表（仅解析后） |

**示例：**

```json
{
  "type": "forward",
  "data": {
    "id": "123456"
  }
}
```

#### node - 合并转发节点

用于构造合并转发消息。仅支持发送。

**引用已有消息：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | string | 转发的消息ID |

**自定义节点：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `user_id` | string | 发送者QQ号 |
| `nickname` | string | 发送者昵称 |
| `content` | string 或 array | 消息内容（字符串或消息段数组） |

**示例：**

```json
{
  "type": "node",
  "data": {
    "id": "123456"
  }
}
```

```json
{
  "type": "node",
  "data": {
    "user_id": "10001000",
    "nickname": "某人",
    "content": [
      {
        "type": "text",
        "data": {
          "text": "转发的消息内容"
        }
      }
    ]
  }
}
```

---

### 特殊消息段

#### json - JSON消息

用于发送JSON格式的卡片消息。

**发送参数：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `data` | string | JSON字符串 |

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `data` | string | JSON数据 |

**示例：**

```json
{
  "type": "json",
  "data": {
    "data": "{\"app\":\"com.tencent.miniapp\",\"desc\":\"\",\"view\":\"notification\",\"ver\":\"1.0.0.11\"}"
  }
}
```

#### xml - XML消息

用于发送XML格式的消息。

**发送参数：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `data` | string | XML内容 |

**接收字段：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `data` | string | XML内容 |

**示例：**

```json
{
  "type": "xml",
  "data": {
    "data": "<?xml version=\"1.0\" encoding=\"utf-8\"?><msg>...</msg>"
  }
}
```

#### markdown - Markdown消息

用于发送Markdown格式的消息。发送时需在双层合并转发内使用。

**示例：**

```json
{
  "type": "markdown",
  "data": {
    "content": "# 标题\n这是**加粗**文本"
  }
}
```

#### lightapp - 小程序卡片

用于发送小程序卡片。接收时为json类型，发送时需要调用扩展接口 `get_mini_app_ark` 获取卡片数据。

**发送方式：**

1. 调用 `get_mini_app_ark` API 获取小程序卡片数据
2. 将返回的数据作为json消息段发送

**接收时：** 作为json类型消息段接收

**注意：** 不能直接构造lightapp消息段发送，需要通过 `get_mini_app_ark` API 获取。

---

## 消息段组合示例

多个消息段可以组合成一条完整的消息：

```json
[
  {
    "type": "at",
    "data": {
      "qq": "10001000"
    }
  },
  {
    "type": "text",
    "data": {
      "text": " 看看这张图片"
    }
  },
  {
    "type": "image",
    "data": {
      "file": "http://example.com/image.jpg"
    }
  }
]
```

这条消息的效果为：@某人 + 文本 + 图片。

---

## 注意事项

1. **数据类型**：除特殊说明外，大部分参数值都为字符串类型，以支持与CQ码格式的互相转换
2. **文件路径**：支持绝对路径（file://协议）、网络URL（http/https）、Base64编码
3. **接收与发送**：某些消息段接收和发送时的字段可能不同，请注意区分
4. **type字段特殊值**：某些消息段（如闪照）通过在data中添加`type`字段来表示特殊类型
5. **JSON类型**：部分消息段（如share、location、music）接收时会转换为json类型
