# Askr Framework 部署和配置指南

**面向框架部署者(机器人所有者)的完整指南**

## 版本信息

适用的框架版本：[Beta 0.2] - *You Asked for This*

文档版本：Beta 0.2.1

最后更新日期：2025-07-07


---

## 部署方式

### 开发环境部署

开发环境适用于测试和调试插件：

```bash
python3 askr_framework.py
```

框架将在配置的端口（默认19219）上监听HTTP请求。

### 生产环境部署

生产环境推荐使用gunicorn进行多线程部署：

```bash
# 推荐配置：1个worker进程，8个线程
gunicorn -w 1 --threads 8 -b 0.0.0.0:19219 askr_framework:NAPCAT_LISTENER
```

**参数说明**：
- `-w 1`：使用1个worker进程（不要增加，框架设计为单进程）
- `--threads 8`：每个worker使用8个线程处理请求
- `-b 0.0.0.0:19219`：绑定地址和端口

#### 3. 使用systemd管理（推荐）

创建服务文件 `/etc/systemd/system/askr-framework.service`：

```ini
[Unit]
Description=Askr Framework QQ Bot
After=network.target

[Service]
Type=exec
User=bot
WorkingDirectory=/path/to/askr-framework
ExecStart=/usr/bin/gunicorn -w 1 --threads 8 -b 0.0.0.0:19219 askr_framework:NAPCAT_LISTENER
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

管理服务：

```bash
# 重新加载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start askr-framework

# 设置开机自启
sudo systemctl enable askr-framework

# 查看状态
sudo systemctl status askr-framework

# 查看日志
sudo journalctl -u askr-framework -f
```

### 健康检查

框架提供 `/health` 端点用于监控：

```bash
curl http://localhost:19219/health
```

返回示例：
```json
{
  "status": "healthy",
  "timestamp": 1703123456,
  "active_plugins": 2,
  "is_muted": false,
  "version": "Beta 0.98",
  "NapCatServerStatus": "OK"
}
```

---

## 配置文件说明

### frameworkConfig.json

框架主配置文件，可选。如果不存在，框架使用默认配置。

**完整配置示例**：

```json
{
  "version": "1.0",
  "NAPCAT_SERVER": {
    "api_url": "http://localhost:19218"
  },
  "NAPCAT_LISTEN": {
    "host": "0.0.0.0",
    "port": 19219
  },
  "PATHS": {
    "plugins_dir": "./plugins",
    "database_file": "./EventHistory.db",
    "access_control": "./PluginsAccessControl.json"
  },
  "HTTP": {
    "max_retries": 3,
    "timeout_seconds": 10,
    "status_check_timeout": 5
  },
  "PLUGIN_EXECUTION": {
    "max_cpu_time_seconds": 3.0,
    "max_wall_time_seconds": 30.0,
    "memory_limit_mb": 1024,
    "monitor_interval_seconds": 0.1,
    "process_creation_method": "spawn"
  },
  "ADMIN_NOTIFICATION": {
    "enabled": true,
    "admin_qq": 123456789,
    "notify_level": "ERROR",
    "rate_limit_seconds": 1200,
    "message_format": "Askr Alert \n[{level}] {time}\n{message}"
  }
}
```

#### 配置项详解

**NAPCAT_SERVER**
- `api_url`：NapCat HTTP API地址，框架向此地址发送API请求

**NAPCAT_LISTEN**
- `host`：框架监听地址，`0.0.0.0`表示监听所有网卡
- `port`：框架监听端口，NapCat需要向此端口发送事件

**PATHS**
- `plugins_dir`：插件目录路径
- `database_file`：SQLite数据库文件路径
- `access_control`：访问控制配置文件路径

**HTTP**
- `max_retries`：API调用失败重试次数
- `timeout_seconds`：API调用超时时间
- `status_check_timeout`：状态检查超时时间

**PLUGIN_EXECUTION**
- `max_cpu_time_seconds`：插件最大CPU时间限制
- `max_wall_time_seconds`：插件最大执行时间限制
- `memory_limit_mb`：插件内存限制（MB）
- `monitor_interval_seconds`：资源监控间隔
- `process_creation_method`：进程创建方式（保持默认"spawn"）

**ADMIN_NOTIFICATION**
- `enabled`：是否启用管理员通知
- `admin_qq`：管理员QQ号
- `notify_level`：通知级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- `rate_limit_seconds`：相同消息的通知间隔（秒）
- `message_format`：通知消息格式模板

#### 配置注意事项

1. **只需提供要修改的配置项**，未提供的使用默认值
2. **类型验证**：框架会验证配置值的类型和范围
3. **关键配置错误**：某些配置错误（如api_url格式错误）会导致框架退出
4. **路径自动创建**：目录类配置项会自动创建不存在的目录

### PluginsAccessControl.json

插件访问控制配置文件，用于限制插件的触发条件和权限。

**配置示例**：

```json
{
  "version": "1.0",
  "default_policy": "allow",
  "rules": {
    "global": {
      "private": {
        "BlackList": [999999]
      },
      "group": {
        "BlackList": [666666]
      },
      "privilege": false
    },
    "admin_plugin.py": {
      "private": {
        "WhiteList": [123456, 789012]
      },
      "group": {
        "WhiteList": [111111, 222222]
      },
      "privilege": true
    },
    "game_plugin.py": {
      "private": {},
      "group": {
        "WhiteList": [333333, 444444]
      }
    }
  }
}
```

#### 配置结构说明

**顶层字段**：
- `version`：配置文件版本
- `default_policy`：默认策略，可选值：`"allow"`（默认允许）或`"deny"`（默认拒绝）
- `rules`：访问规则配置

**rules配置**：
- `global`：全局默认规则，适用于所有未特别配置的插件
- `插件名.py`：特定插件的规则（插件文件名必须包含.py后缀）

**每个规则包含**：
- `private`：私聊规则
  - `WhiteList`：白名单QQ号列表（数组）
  - `BlackList`：黑名单QQ号列表（数组）
- `group`：群聊规则
  - `WhiteList`：白名单群号列表（数组）
  - `BlackList`：黑名单群号列表（数组）
- `privilege`：是否有跨域配置访问权限（布尔值）

对于同一插件、同一场景，白名单和黑名单只能二选一（如某插件的群聊规则，只能有白名单或黑名单；如果两者都提供，初始化阶段会弹出警告，且只有白名单会生效）。
如果同时配置了全局规则和针对特定插件的规则，以针对特定插件的规则优先。
#### 访问控制逻辑

1. **优先级规则**：
   - 插件特定规则 > global规则
   - WhiteList（白名单）> BlackList（黑名单）
   - 无匹配规则时使用default_policy

2. **privilege权限**：
   - 设置为`true`的插件可以读写其他插件的配置
   - 用于实现管理类插件
   - 所有跨域访问会记录日志

3. **使用建议**：
   - 对于管理类插件，使用白名单限制只有管理员可用
   - 对于娱乐类插件，可以用黑名单排除问题用户
   - 对于测试插件，可以限制在特定群聊中使用

---

## 管理员通知系统

### 功能说明

管理员通知系统允许框架在发生重要事件时通过QQ消息通知管理员。

### 通知级别

- **DEBUG**：调试信息（一般不建议在生产环境使用）
- **INFO**：一般信息
- **WARNING**：警告信息
- **ERROR**：错误信息（推荐）
- **CRITICAL**：严重错误

### 通知场景

1. **插件错误**：插件执行时发生异常
2. **资源超限**：插件超过CPU、内存或时间限制
3. **初始化失败**：插件INITIALIZER函数执行失败
4. **框架关闭**：收到关闭信号时（如果启用）
5. **自定义日志**：插件使用logging模块记录的相应级别日志

### 防刷屏机制

- 相同消息在`rate_limit_seconds`时间内只通知一次
- 默认1200秒（20分钟）
- 基于消息内容的hash值判断是否相同

### 管理员命令

管理员可以通过私聊发送以下命令控制框架：

- **`mute`**：立即停止所有机器人活动（紧急停止）
- **`unmute`**：恢复正常运行

**使用场景**：
- 插件失控导致大量消息发送
- 外部API故障需要临时停止
- 紧急维护期间

---

## 最佳实践

### 安全建议

1. **网络安全**：
   - 生产环境中限制监听地址，避免直接暴露在公网
   - 使用防火墙限制访问来源
   - 考虑使用反向代理增加安全层

2. **访问控制**：
   - 为管理类插件设置严格的白名单
   - 定期审查访问控制配置
   - 及时更新黑名单

3. **资源限制**：
   - 根据服务器性能调整插件资源限制
   - 监控系统资源使用情况
   - 避免同时运行过多资源密集型插件

### 维护建议

1. **日志管理**：
   - 配置日志轮转避免磁盘占满
   - 定期检查错误日志
   - 保留重要日志用于问题排查

2. **数据备份**：
   - 定期备份`EventHistory.db`数据库
   - 备份插件配置数据
   - 备份访问控制配置

3. **监控告警**：
   - 使用健康检查端点进行监控
   - 设置适当的通知级别
   - 配置外部监控系统

### 插件管理

1. **插件选择**：
   - 优先选择经过测试的稳定插件
   - 避免功能重复的插件
   - 注意插件之间的兼容性

2. **插件更新**：
   - 更新前先在测试环境验证
   - 保留旧版本以便回滚
   - 查看插件更新日志

3. **性能优化**：
   - 使用访问控制减少不必要的插件调用
   - 合理设置UNCONDITIONAL插件的执行间隔
   - 监控插件执行时间和资源使用

---
