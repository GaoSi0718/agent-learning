# 21 · TCP 三次握手 + TIME_WAIT（要能讲清 why）

> 来源：冲刺版 §5.1 B 轨必考-21｜ 完整版：l0_bank/network_50.md 题 4/6（本文件是面试答法骨架）

## 30 秒答
三次握手 SYN → SYN+ACK → ACK：全双工双方都要通告初始序号并确认；两次的问题是一个迟到的历史 SYN 会让服务端单方面建连白等资源——第三次 ACK 给客户端否决权。TIME_WAIT 是主动关闭方停留 2MSL 的状态：①保证最后的 ACK 丢失后还能应答对端重传的 FIN；②让旧报文自然消亡，不污染相同四元组的新连接。

## 2 分钟答法骨架（讲 why 不背名词）
- **seq/ack 数字演变要能现场写**：c→s SYN(seq=x)；s→c SYN+ACK(seq=y, ack=x+1)；c→s ACK(ack=y+1)——ISN 随机化的原因也顺带讲（防历史段注入/序号预测）；
- **四次挥手 vs 三次握手**：挥手多一次是因为全双工——被动方收到 FIN 时可能还有数据要发（CLOSE_WAIT 半关闭），ACK 与 FIN 分开；
- **TIME_WAIT 实战题**：大量 TIME_WAIT 出现在**主动关闭方**——服务端出现说明它在频繁主动断连，正确解法是长连接/连接池/让客户端先关，而不是无脑开 tcp_tw_reuse；
- **实验佐证**：我们 W6 v1.5 起用 SSE 长连接推送（避免每请求建连），echo_server.py 可现场演示连接建立-回显-关闭全过程。

## 追问预案（3 层）
1. 「SYN Flood 怎么防？」→ syncookies 把连接信息编进序号不占半连接队列（计算换内存），配合 backlog/重试参数；
2. 「2MSL 具体多长？」→ Linux MSL=30s → TIME_WAIT≈60s；所以连接池要管好「主动关闭的代价」；
3. 「为什么 HTTP/2 一条连接上多路复用还会被队头阻塞？」→ TCP 字节流严格有序，一段丢失堵所有 Stream——QUIC 在传输层解决（network_50 题 17）。

## 素材
l0_bank/network_50.md 题 4/6/17、notes/os/echo_server.py
