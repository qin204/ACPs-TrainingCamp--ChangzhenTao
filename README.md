# 简易 C/S 聊天示例（Python + asyncio）

## 项目简介
这是一个基于 TCP + JSON 行协议实现的简易聊天中转服务器与控制台客户端。支持多用户注册、在线列表、邀请建立一对一会话、私聊消息转发、离线与会话中断处理。

适合作为学习：
- Python `asyncio` TCP 通信
- JSON per line 消息协议
- 多用户会话管理
- 并发聊天测试

## 目录结构
- `server.py`：异步聊天服务器
- `client.py`：控制台聊天客户端
- `test_multi_pairs.py`：并发会话自动化测试（A↔B 与 C↔D）
- `sync_test.py`：同步阻塞式测试客户端示例
- `test_client.py`：客户端测试脚本（如果存在，可用于单元或集成测试）

## 运行环境
- Python 3.8+
- 纯标准库实现，无额外依赖

## 快速启动
1. 启动服务器：

   ```bash
   python server.py --host 127.0.0.1 --port 8888
   ```

2. 启动客户端：

   ```bash
   python client.py --host 127.0.0.1 --port 8888
   ```

3. 输入用户名，例如 `A`。
4. 在其他终端重复启动客户端并输入不同用户名，例如 `B`、`C`、`D`。

## 客户端命令说明
- `/list`
  - 列出当前在线的其他用户
- `/invite <user>`
  - 向指定用户发送邀请，请求建立一对一会话
- `/accept <user>`
  - 接受来自指定用户的会话邀请
- `/msg <user> <message>`
  - 在会话中向指定用户发送私聊消息
- `/leave`
  - 结束当前会话
- `/quit`
  - 退出客户端程序

## 使用示例
A 与 B 建立会话的流程：

1. A 输入 `/list` 查看在线用户
2. A 输入 `/invite B`
3. B 收到邀请后输入 `/accept A`
4. A 和 B 互相发送消息：
   - ` /msg B 你好 B`
   - ` /msg A 你好 A`
5. 任一方输入 `/leave` 结束会话

## 测试
### 并发会话测试
执行自动化测试脚本，验证服务器是否支持多组并发会话：

```bash
python test_multi_pairs.py
```

### 同步测试客户端
可以用同步阻塞客户端模拟 initiator/responder：

```bash
python sync_test.py --name A --role initiator --target B
python sync_test.py --name B --role responder
```

## 实现细节
- `server.py`：
  - 首条消息必须为 `register` 注册用户名
  - 支持 `list`、`invite`、`accept`、`message`、`leave` 操作
  - 使用 `USERS` 和 `SESSIONS` 字典维护在线用户与会话关系
- `client.py`：
  - 使用 `asyncio` 并发处理输入与服务器消息
  - 采用 JSON 行协议与服务器通信
  - 处理服务器返回的列表、邀请、会话建立、消息与断开通知

## 注意事项
- 当前未启用加密，建议仅在受信网络或本地测试环境中运行
- 未实现持久化消息历史，断线后会话信息丢失
- 可扩展方向：群聊、身份验证、TLS/SSL、WebSocket 前端、消息存档、UI 界面等

## 贡献与扩展
欢迎改进：
- 支持更复杂的会话管理
- 处理用户名冲突与重连
- 支持群聊、离线消息、消息存储
- 添加更好的命令帮助界面
