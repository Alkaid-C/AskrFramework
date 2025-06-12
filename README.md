# Askr Framework

## 让QQ机器人开发像写Hello World一样简单

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-linux-lightgrey.svg)](https://www.linux.org/)

---

想要一个复读机器人？只需要3行代码：

```python
MANIFEST = {"MESSAGE_PRIVATE": "复读机"}

def 复读机(simpleEvent):
    return simpleEvent["text_message"]
```

就是这么简单！ 🎉

---

## 核心理念

**让复杂的事情变简单，让简单的事情变有趣**

Askr Framework基于[NapCat](https://github.com/NapNeko/NapCatQQ)项目，专注于降低QQ机器人的开发门槛。我们相信，每个有想法的人都应该能够轻松创造属于自己的智能助手。

### 极简开发体验

使用Askr Framework搭建QQ机器人只需要了解：
- ✅ 如何定义一个函数和其返回值
- ✅ 如何读写字典类型变量

而直接面向NapCat开发，你需要掌握：
- ❌ HTTP服务器搭建
- ❌ 复杂的多层嵌套数据解析
- ❌ 并发控制和线程安全
- ❌ 历史消息数据库管理
- ❌ 错误处理和系统监控

**同样的复读机器人，不同框架需要多少代码？**

| 框架 | 代码行数 | 编程语言 | 对新手开发者可能的难点 |
|------|----------|----------|------------------------|
| **Askr Framework** | **3** | **Python** | **无** |
| Koishi | 5+配置文件 | TypeScript | **函数式编程**、**箭头函数**(=>) |
| NcatBot | 5 | Python | **装饰器**(@)、**异步编程**(async/await) |
| NoneBot2 | 6+配置文件 | Python | **装饰器**(@)、**异步编程**(async/await) |
| Mirai | 15 | Kotlin/Java | **面向对象编程**、**语言学习成本** |

### 渐进式学习路径

Askr Framework提供了从简单到复杂的平滑学习曲线。你可以从最基础的功能开始，每掌握一个新概念，机器人就变得更强大更有趣。

**兴趣驱动的成长**：当你看到简单的复读机器人工作时，自然会想"能不能让它更聪明一点？"。当你实现了智能回复，又会想"能不能记住用户说过什么？"。每个想法都对应一个新的技术点，而每个技术点都让你的机器人功能更上一层楼。

**渐进式的复杂度**：框架设计让你可以逐步接触更多功能，而不是一开始就被复杂的概念吓倒。今天学会基本回复，明天学会读取配置，后天学会调用API——每一步都建立在前一步的基础上，让学习变得自然而有趣。

---

## 为新手开发者而生

### 防御性框架设计

作为面向初级开发者的框架，Askr Framework内置了多重保护机制：

#### 进程隔离保护

Askr Framework采用独特的**框架多线程+插件多进程**混合架构，这在QQ机器人框架中是独一无二的设计选择。

**与主流框架的技术对比**：
- **其他主流框架**（NoneBot2、NcatBot、Koishi等）都采用协程模型，追求更高的性能表现
- **协程模型的风险**：当某个插件出现严重bug（死循环、内存泄漏、阻塞调用）时，可能影响整个机器人系统
- **Askr的选择**：每个插件在独立进程中运行，提供绝对的错误隔离

**进程隔离的优势**：
- **插件崩溃不影响框架**：单个插件的任何错误都无法影响主框架和其他插件
- **精确资源控制**：自动限制CPU时间、内存使用、执行时间
- **自动故障恢复**：异常插件被自动终止，系统继续正常运行

**性能权衡**：
虽然进程隔离会带来一定的性能开销，但Askr通过优化的混合并行架构仍能提供可接受的性能表现。此外我们通过扩展OneBot 11 API实现了前级消息过滤，在[跑团骰娘](sample_plugins/Dice.py)等典型场景中实现了与协程框架相似甚至更好的性能。

#### 全方位错误保护机制

**智能错误通知**：
- **实时警报**：插件出错时立即通知管理员QQ
- **智能防刷屏**：相同错误5分钟内只通知一次
- **分级通知**：可配置通知级别（ERROR/WARNING/INFO）

**紧急控制能力**：
- **一键静音**：管理员发送"mute"立即停止所有机器人活动
- **快速恢复**：发送"unmute"恢复正常运行
- **适用场景**：插件失控、外部API故障、紧急维护

**温和的错误处理**：
- **优雅降级**：单个插件出错不影响其他插件
- **自动重试**：网络请求失败自动重试
- **详细日志**：完整的错误信息帮助调试

**这意味着**：即使你是编程新手，即使你的代码有bug，框架也能确保系统稳定运行，给你足够的时间学习和改进。

---

##  快速开始

### 系统要求

- **操作系统**: Linux
- **Python版本**: 3.12+
- **依赖软件**: NapCat QQ机器人框架

### 安装步骤

#### 1. 安装Python依赖
```bash
pip install flask requests psutil
```

#### 2. 部署NapCat

参考[NapCat部署文档](https://napneko.github.io/)，部署NapCat并登录QQ号。你需要：

1. 打开一个HTTP Server，并将主机和端口设为Askr Framework的上报地址。（如主机设为localhost, 端口设为19217）
2. 打开一个HTTP Client，并将URL设为Askr Framework监听的URL。（如将URL设为http://localhost:19218）

#### 3. 配置Askr Framework

编辑`askr_framework.py`中的CONFIG部分，确保端口配置与NapCat设置相匹配：

```python
CONFIG = {
    'NAPCAT_SERVER': {
        'api_url': 'http://localhost:19217',  # 对应NapCat的HTTP Server端口
    },
    'NAPCAT_LISTEN': {
        'host': '0.0.0.0',
        'port': 19218  # 对应NapCat HTTP Client的目标URL端口
    },
    'ADMIN_NOTIFICATION': {
        'enabled': True,               # 启用错误通知
        'admin_qq': 123456789,         # 改为你的QQ号
        'notify_level': 'ERROR',       # 通知级别
    }
}
```

**配置说明**：
- `NAPCAT_SERVER.api_url`：Askr向NapCat发送API请求的地址
- `NAPCAT_LISTEN.port`：Askr接收NapCat事件推送的端口
```

#### 4. 创建第一个插件

在`plugins/`目录下创建`hello.py`：
```python
MANIFEST = {"MESSAGE_PRIVATE": "你好世界"}

def 你好世界(simpleEvent):
    return f"你好！你说了：{simpleEvent['text_message']}"
```

#### 5. 启动框架

**开发环境**（单线程）：

```bash
python askr_framework.py
```

**生产环境**（推荐多线程）：

```bash
pip install gunicorn
gunicorn -w 1 --threads 8 -b 0.0.0.0:19218 askr_framework:NAPCAT_LISTENER
```

现在给机器人发私聊消息试试！🎊

---

## 文档

- **[快速教程](tutorial.md)** - Step-by-step项目教程，从复读机器人到高级应用
- **[API文档](api_reference.md)** - 详细的API参考和最佳实践  
- **[架构文档](architecture.md)** - 深入了解框架设计理念
- **[实现细节](technical_guide.md)** - 准备给项目贡献代码

### 示例插件库

- [雷诺曼占卜](sample_plugins/Lenormand.py) --通过云端LLM API实现的雷诺曼占卜机器人。监听群聊消息，simpleEvent&rawEvent入参，string返回值。
- [跑团骰娘](sample_plugins/Dice.py) -- COC跑团用骰娘，实现了[溯回骰](https://github.com/Dice-Developer-Team/DiceV2Docs/blob/master/User_Manual.md)所支持的大多数功能。监听初始化、私聊群聊消息，simpleEvent&rawEvent入参，string/dict/list返回值
- [b站up主动态更新播报](sample_plugins/BiliDynamicsUpdate.py) -- 调用[bilibili-api](https://github.com/Nemo2011/bilibili-api/)，获取指定up主的动态更新，监听初始化、无条件事件，botContext入参，list返回值。

---

##  技术特点

### 混合并行架构
- **Framework层**：多线程并发启动插件
- **Plugin层**：多进程隔离执行，资源独立
- **Response机制**：完成插件立即返回，无需等待其他插件

### 智能事件过滤
- **MESSAGE_GROUP_MENTION**：仅响应群聊中@机器人的消息
- **MESSAGE_GROUP_BOT**：仅响应以 `.` `/` `\` 开头的指令消息
- **性能优化**：避免普通群聊消息触发插件，大幅减少不必要的进程创建，在骰娘、指令机器人等典型场景中达到与其他框架相似的性能表现

### 事件驱动设计
- **统一事件模型**：消息、通知、请求均抽象为事件
- **声明式注册**：MANIFEST字典声明事件处理关系
- **事件继承机制**：支持事件类型的层级响应

### 函数式插件接口
- **三要素设计**：声明、输入参数、返回值
- **参数按需选择**：simpleEvent、rawEvent、botContext任选
- **多格式返回**：字符串、字典、列表统一处理

---

## 相关项目

- **[NapCat项目](https://github.com/NapNeko/NapCatQQ)** - 提供与QQ通信的核心能力
- **[OneBot标准](https://github.com/botuniverse/onebot-11)** - 统一的聊天机器人协议规范

---

##  开源协议

本项目采用 [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html) 开源协议。

**这意味着**：
- ✅ 你可以自由使用、修改和分发本软件
- ✅ 你可以将其用于商业用途
- ⚠️ 修改后的版本必须同样开源
- ⚠️ 必须保留原作者信息和协议声明

---

##  立即开始你的机器人之旅

从一个简单的复读机器人开始，在兴趣驱动下逐步学习更复杂的功能。

**Askr Framework** - 让复杂的QQ机器人开发变得简单而有趣！

现在就创建你的第一个插件，开始探索无限可能吧！ 

声明：本项目的文档中包含AI生成的内容。
