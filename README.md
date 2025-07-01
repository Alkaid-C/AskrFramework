# Askr Framework

## 让QQ机器人开发像写Hello World一样简单

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-linux-lightgrey.svg)](https://www.linux.org/)
[![Version](https://img.shields.io/badge/version-Beta%200.98-orange.svg)](https://github.com/yourusername/askr-framework)

---

想要一个复读机器人？只需要3行代码：

```python
MANIFEST = {"MESSAGE_PRIVATE": "复读机"}

def 复读机(simpleEvent):
    return simpleEvent["text_message"]
```

就是这么简单！

---

## 核心理念

**让复杂的事情变简单，让简单的事情变有趣**

Askr Framework基于[NapCat](https://github.com/NapNeko/NapCatQQ)项目，专注于降低QQ机器人的开发门槛。我们相信，每个有想法的人都应该能够轻松创造属于自己的智能助手。

### 为什么选择Askr Framework？

**极简开发体验**

使用Askr Framework搭建QQ机器人只需要了解：
- 如何定义一个函数和其返回值
- 如何读写字典类型变量

而直接面向NapCat开发，你需要掌握：
- HTTP服务器搭建
- 复杂的多层嵌套数据解析  
- 并发控制和线程安全
- 历史消息数据库管理
- 错误处理和系统监控

**代码量对比**

同样的复读机器人，不同框架需要多少代码？

| 框架 | 代码行数 | 编程语言 | 对新手开发者的难点 |
|------|----------|----------|----------------------|
| **Askr** | **3** | **Python** | **无** |
| Koishi | 5+配置文件 | TypeScript | 函数式编程、箭头函数(=>) |
| NcatBot | 5 | Python | 装饰器(@)、异步编程(async/await) |
| NoneBot2 | 6+配置文件 | Python | 装饰器(@)、异步编程(async/await) |
| Mirai | 15 | Kotlin/Java | 面向对象编程、语言学习成本 |

### 渐进式学习路径

Askr Framework提供了从简单到复杂的平滑学习曲线。你可以从最基础的功能开始，每掌握一个新概念，机器人就变得更强大。

**兴趣驱动的成长**：当你看到简单的复读机器人工作时，自然会想"能不能让它更聪明一点？"。当你实现了智能回复，又会想"能不能记住用户说过什么？"。每个想法都对应一个新的技术点，而每个技术点都让你的机器人功能更上一层楼。

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

#### 全方位错误保护机制

**智能错误通知**：
- **实时警报**：插件出错时立即通知管理员QQ
- **智能防刷屏**：相同错误20分钟内只通知一次
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

## 技术特点

### 混合并行架构
- **Framework层**：多线程并发启动插件
- **Plugin层**：多进程隔离执行，资源独立
- **Response机制**：完成插件立即返回，无需等待其他插件

### 智能事件过滤
- **MESSAGE_GROUP_MENTION**：仅响应群聊中@机器人的消息
- **MESSAGE_GROUP_BOT**：仅响应以 `.` `/` `\` 开头的指令消息
- **性能优化**：避免普通群聊消息触发插件，大幅减少不必要的进程创建
- **访问控制**：通过配置文件实现更精细的过滤

### 生产级特性
- **外部配置管理**：支持JSON配置文件，无需修改代码
- **访问控制系统**：基于私聊/群聊的黑白名单机制
- **权限管理**：支持跨插件配置访问的权限控制
- **优雅关闭**：收到信号后等待插件完成再退出
- **健康检查**：提供HTTP端点用于监控

### 函数式插件接口
- **三要素设计**：声明、输入参数、返回值
- **参数按需选择**：simpleEvent、rawEvent、botContext任选
- **多格式返回**：字符串、字典、列表统一处理

---

## 框架定位

### 适合Askr的场景

**学习与原型环境**：
- 新手开发者学习QQ机器人开发
- 快速验证想法和功能原型

**稳定性优先场景**：
- 无法容忍插件错误影响整体服务
- 需要运行多个不同来源的插件
- 团队中包含编程新手

**生产环境场景**：
- 需要外部配置管理
- 要求优雅关闭支持
- 需要细粒度访问控制
- 需要插件间协调管理

### 不适合Askr的场景

**高性能要求场景**：
- 需要毫秒级响应的高频交互
- 需要长时间CPU密集计算的任务
- 严格的实时性响应要求

**复杂应用场景**：
- 需要插件间复杂交互的应用
- 复杂的状态管理需求
- 需要高度定制化的业务逻辑

---

## 快速开始

### 系统要求

- **操作系统**: Linux
- **Python版本**: 3.12+
- **依赖软件**: NapCat QQ机器人框架

### 1. 安装Python依赖

```bash
pip install flask requests psutil
```

### 2. 部署NapCat

参考[NapCat官方文档](https://napneko.github.io/)部署NapCat并登录QQ号。

**!!!重要!!!** 配置NapCat时需要：
- 设置HTTP上报地址为Askr Framework的监听地址（默认：`http://localhost:19219`）
- 设置HTTP API地址供Askr Framework调用（默认：`http://localhost:3000`）

### 3. 创建第一个插件

在`plugins/`目录下创建`hello.py`：

```python
MANIFEST = {"MESSAGE_PRIVATE": "你好世界"}

def 你好世界(simpleEvent):
    return f"你好！你说了：{simpleEvent['text_message']}"
```

### 4. 启动框架

```bash
python askr_framework.py
```

现在给机器人发私聊消息试试！

---

## 文档体系

- **[部署指南](Owner_Guide.md)** - 部署配置和管理员功能
- **[快速教程](Tutorial.md)** - 7个渐进式插件开发教程
- **[API文档](API_Reference.md)** - 详细的API参考
- **[技术指南](Technical_Guide.md)** - 高级特性和最佳实践
- **[架构文档](Architecture.md)** - 框架内部架构说明

### 示例插件库

我们提供了丰富的示例插件，展示框架的各种能力：
- 基础功能示例（复读、关键词回复）
- 群管理工具（欢迎新人、违禁词检测）
- 娱乐插件（签到系统、小游戏）
- 实用工具（天气查询、定时提醒）
- 高级功能（插件管理器、配置中心）

---

## 相关项目

- **[NapCat项目](https://github.com/NapNeko/NapCatQQ)** - 提供与QQ通信的核心能力
- **[OneBot标准](https://github.com/botuniverse/onebot-11)** - 统一的聊天机器人协议规范

---

## 开源协议

本项目采用 [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html) 开源协议。

**这意味着**：
- 你可以自由使用、修改和分发本软件
- 你可以将其用于商业用途
- 修改后的版本必须同样开源
- 必须保留原作者信息和协议声明

---

## 立即开始你的机器人之旅

从一个简单的复读机器人开始，在兴趣驱动下逐步学习更复杂的功能。

**Askr Framework - 让QQ机器人开发变得简单而有趣！**