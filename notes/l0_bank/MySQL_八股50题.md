# L0 题库 · MySQL 50 题

> **用途/格式/口径**：同 network_50.md。**高频重点**：索引结构（B+树）与失效、事务隔离级别与 MVCC、锁、日志体系（redo/undo/binlog）、慢查询与 EXPLAIN。
> 主版本口径：MySQL 8.0（InnoDB）。

---

## 一、体系结构（4 题）

### 1. MySQL 的分层架构？
- **简答**：连接层（连接池/鉴权）→ 服务层（SQL 接口/解析器/优化器/缓存）→ 存储引擎层（InnoDB 等可插拔）。
- **深答**：一条 SQL 的旅程：连接器（TCP+认证+权限快照）→ 分析器（词法/语法树）→ 优化器（选索引、join 顺序、改写）→ 执行器调引擎 API → 引擎按行取数返回。8.0 已移除查询缓存（失效太频繁）。可插拔引擎的意义：InnoDB 事务行锁、MyISAM 表锁全文索引（已边缘化）、Memory 内存表。面试答法：分层+每层一个代表职责+一句「优化器选错索引怎么办（force index/统计信息更新）」。
- **来源**：《高性能 MySQL》第 1 章；MySQL 官方手册 Architecture

### 2. 一条 UPDATE 的完整流程（含日志）？
- **简答**：buffer pool 改页（脏页）→ 写 undo（回滚）→ 写 redo（崩溃恢复）→ 写 binlog（复制/恢复）→ 两阶段提交。
- **深答**：顺序细节：先记 undo 保证回滚与 MVCC；改内存页为脏页；redo log buffer 记「物理修改」；提交时按两阶段提交——redo prepare → 写 binlog → redo commit，保证 redo 与 binlog 一致（否则主从不一致）。脏页由后台线程刷盘，checkpoint 推进。面试常追问：为什么不是直接写磁盘——随机写太贵，redo 是顺序写（呼应 OS 题 23）。
- **来源**：《MySQL 实战 45 讲》第 2、15 讲；MySQL 官方手册 InnoDB Redo Log

### 3. undo log 与 redo log 的区别？
- **简答**：undo 记「反向操作」用于回滚与 MVCC 读旧版本；redo 记「物理重做」用于崩溃后重放，保证持久性。
- **深答**：undo 是逻辑日志（insert 对应 delete），存在 undo 表空间，长事务会让 undo 无法清理（版本链变长、空间膨胀）——「长事务危害」的标准答案之一；redo 是物理日志（页级修改），循环写，checkpoint 之前不能覆盖。两者配合实现 ACID 的 A（回滚）、C（约束）、D（redo）、以及 I 下的 MVCC。
- **来源**：《MySQL 实战 45 讲》相关讲次；MySQL 官方手册 Undo Logs

### 4. binlog 是什么？与 redo log 的区别？三种格式？
- **简答**：binlog 是服务层逻辑日志（所有引擎共用）用于复制与时间点恢复；redo 物理且引擎私有；格式：statement/row/mixed。
- **深答**：statement 记 SQL 文本（体积小但 NOW()/UUID() 等不确定函数导致主从不一致）；row 记行级变更（大但精确，默认）；mixed 自动切换。主从复制流程：主写 binlog → dump 线程推送 → 从 IO 线程写 relay log → SQL 线程重放。引申：binlog 也是「误删数据恢复」的依据（flashback 工具解析 row 格式）。
- **来源**：MySQL 官方手册 Binary Log；《MySQL 实战 45 讲》

## 二、索引（10 题）

### 5. B+树为什么适合做索引？与 B 树/哈希/红黑树对比？
- **简答**：矮胖多叉（3-4 层装千万行）、叶子链表利于范围扫描；哈希不支持范围，红黑树太高 IO 多，B 树非叶也存数据使扇出变小。
- **深答**：磁盘 IO 按页（16KB），B+树非叶节点只存键+指针，扇出上千，2000 万行约 3 层=最多 3 次页读（根常驻内存，实际 1-2 次）。叶子节点双向链表支持范围查询与排序遍历。对比哈希：等值 O(1) 但无法 range/order by/最左前缀。InnoDB 自适应哈希是自动热点缓存，不是建索引选项。引申：为什么不用跳表——内存结构（Redis zset 用），磁盘更爱多叉矮树。
- **来源**：《高性能 MySQL》第 5 章；《MySQL 技术 内幕：InnoDB 存储引擎》第 5 章

### 6. 聚簇索引与二级索引？什么是回表？
- **简答**：聚簇索引叶子存整行（InnoDB 主键）；二级索引叶子存主键值，查非索引列要回表再查一次聚簇索引。
- **深答**：回表成本=二级索引树高 + N 次主键查找，所以覆盖索引（查询列全在索引里）能省回表——EXPLAIN Extra 出现 Using index 即覆盖。设计推论：主键要短（所有二级索引都带它）、自增主键写入顺序且避免页分裂。面试高频变体：select * vs select 指定列在索引设计上的差异。
- **来源**：《高性能 MySQL》第 5 章；《MySQL 实战 45 讲》

### 7. 最左前缀原则怎么用？
- **简答**：联合索引 (a,b,c) 只能从最左列开始连续命中：a、ab、abc 可用，b/c 单独不行；范围查询后的列停止索引使用。
- **深答**：索引按 (a,b,c) 字典序排列，跳过 a 就无序可言；`where a=1 and b>2 and c=3` 中 b 用范围后 c 只能在 b 命中的范围内过滤（索引条件下推 ICP 可下推过滤减少回表）。设计方法：等值列放前、范围列放后；把高频「a=X order by b」场景做成 (a,b) 免 filesort。追问：`where b=2 order by a` 与 `order by b,a` 能否用同一索引——不能，顺序相反。
- **来源**：《高性能 MySQL》第 5 章；MySQL 官方手册 Multiple-Column Indexes

### 8. 索引失效的常见场景？
- **简答**：对索引列做函数/运算、隐式类型转换、前导 % 模糊、or 连接非索引列、违反最左前缀、优化器判回表太贵全表扫。
- **深答**：原理一句话：让索引「无序」或「无法定位」都会失效——`where phone=13800001111`（字符串列传数字）触发隐式转换等价于套函数；`like '%xx'` 前缀未知无法走树。优化器角度：二级索引回表比例过高时（如命中 30% 行），MySQL 认为全表扫更便宜——所以「有索引不走索引」不一定是 bug。排查：EXPLAIN 看 type/key/rows，`ANALYZE TABLE` 更新统计信息，必要时 force index。
- **来源**：《高性能 MySQL》第 6 章；MySQL 官方手册 Index Extensions/EXPLAIN

### 9. 什么是覆盖索引与索引下推（ICP）？
- **简答**：覆盖索引=查询列全在索引内免回表；ICP=把 where 条件在引擎层用索引数据先过滤再回表。
- **深答**：覆盖索引实例：联合索引 (user_id, status) 下 `select status from t where user_id=?` 全程不回表。ICP 实例：索引 (a,b)，`where a=1 and b like 'x%'`，5.6 前引擎按 a 找到所有行回表再由服务层过滤 b；开启 ICP 后引擎层直接用 b 过滤，回表量骤减，EXPLAIN 显示 Using index condition。这两个是「索引优化怎么落地」的具体抓手。
- **来源**：MySQL 官方手册 Index Condition Pushdown；《高性能 MySQL》

### 10. 主键为什么推荐自增？UUID 做主键的问题？
- **简答**：自增保证顺序追加写不分裂页；UUID 无序导致频繁页分裂/碎片、且二级索引普遍变大。
- **深答**：聚簇索引按主键有序，随机主键（UUIDv4）每次插入落在随机位置→页满后分裂、缓冲池命中率下降、写放大；UUID 做主键还会被每个二级索引叶子携带（36 字节 vs 8 字节 bigint）。折中：有序 UUID（UUIDv7/雪花 ID）兼顾唯一与趋势递增，是分布式分库分表场景的标准答案。面试可补一句：业务主键（身份证号）不做聚簇主键——可变更列做主键是灾难。
- **来源**：《高性能 MySQL》第 5 章；《MySQL 技术 内幕》第 4 章需复核

### 11. 什么是前缀索引与索引选择性？
- **简答**：对长字符串列取前 n 字符建索引省空间；选择性=不重复值/总数，越接近 1 越好。
- **深答**：前缀索引 `index(email(10))` 用选择性曲线找平衡点：`select count(distinct left(email,n))/count(*)` 逼近全列选择性即可。代价：前缀索引不能覆盖索引/排序。替代方案：哈希列（额外列存 CRC32(email) 建索引+等值查询）。选择性的应用也解释了为什么性别列单独建索引没用（选择性≈0.5，优化器不走）。
- **来源**：《高性能 MySQL》第 5 章（前缀索引小节）

### 12. 普通索引 vs 唯一索引怎么选？
- **简答**：查询性能几乎无差；写路径普通索引可用 change buffer 攒批合并，唯一索引必须立刻查重，高频写场景普通索引更优。
- **深答**：唯一索引的价值在约束语义而非性能（业务唯一性兜底）。change buffer：二级索引页不在 buffer pool 时，先记变更等读到再合并——唯一索引因必须读页判重而用不上。结论：能确定业务唯一的用唯一索引（防脏数据优先），纯加速场景用普通索引。
- **来源**：《MySQL 实战 45 讲》相关讲次；MySQL 官方手册 Change Buffer

### 13. 什么是索引跳跃（index skip scan）与松散扫描？group by 如何利用索引？
- **简答**：8.0 的 skip scan 让前缀缺失的查询也能分段用联合索引；group by 若按索引序可直接扫描免临时表。
- **深答**：skip scan：索引 (a,b)，`where b=2` 时 8.0 会枚举每个 a 值做子扫描（a 的 distinct 少时划算）。松散索引扫描：`select max(b) group by a` 沿索引跳读每组首尾即可，EXPLAIN 出现 Using index for group-by。这条答出来能明显超越「背索引失效场景」的普通候选人。
- **来源**：MySQL 8.0 官方手册（Skip Scan Range Access Method）

### 14. 索引会不会太多？代价是什么？
- **简答**：每个索引都拖慢写入（都要同步维护）与占空间，还干扰优化器；按查询收益建，定期清理冗余索引。
- **深答**：代价链：每次 insert/update 同步维护所有索引的 B+树→写放大；优化器候选计划变多、统计成本变高。冗余判断：如 (a) 被 (a,b) 覆盖则 (a) 可删（注意单独 a 的范围查询仍可用 (a,b)？不行——最左前缀含 a 即可，覆盖成立）。工具：sys.schema 的 unused indexes（需运行够长时间才有意义）。
- **来源**：《高性能 MySQL》第 5 章；MySQL sys schema 文档

## 三、事务与 MVCC（9 题）

### 15. 事务 ACID 分别靠什么实现？
- **简答**：原子性 undo 回滚、持久性 redo、隔离性锁+MVCC、一致性是前三者+约束共同的结果。
- **深答**：A：事务失败按 undo 反向补偿；D：redo WAL 先行（提交标志落盘才算成功）；I：写写冲突靠锁，读写冲突靠 MVCC 快照；C：因果上 C 是目的，AID 是手段+应用层约束（外键/唯一键/check）。面试官爱追问「一致性到底是谁保证的」，能答出「应用约束+数据库机制共同」即超预期。
- **来源**：《MySQL 技术 内幕》第 7 章；《MySQL 实战 45 讲》

### 16. 四个隔离级别与各自问题？
- **简答**：读未提交（脏读）→读已提交 RC（不可重复读）→可重复读 RR（幻读，InnoDB 基本解决）→串行化（全冲突）；MySQL 默认 RR。
- **深答**：脏读=读到未提交数据；不可重复读=同事务两次读值不同（他方 update）；幻读=同条件两次读行数不同（他方 insert/delete）。InnoDB RR 用 MVCC（快照读）+ 间隙锁（当前读）把幻读压到基本不出现。互联网公司（含阿里规范）常用 RC：锁范围小、并发好、间隙锁少——能讲清「为什么大厂会改默认」是加分项。
- **来源**：MySQL 官方手册 Transaction Isolation Levels；《MySQL 技术 内幕》第 7 章

### 17. MVCC 的实现原理？
- **简答**：每行藏 trx_id/roll_pointer，undo 组成版本链；事务用 ReadView（活跃事务列表）决定能看哪个版本。
- **深答**：ReadView 四要素：m_ids（生成时活跃事务）、min/max_trx_id、creator_trx_id；可见性判断：版本的 trx_id<min 可见、≥max 不可见、在活跃列表里不可见——不可见就沿 roll_pointer 顺版本链找旧版。RC 每次 select 生成新 ReadView（能读到别人已提交的最新）；RR 复用第一次的 ReadView（整个事务一个快照）。这解释了 RC/RR 行为差异的全部。
- **来源**：《MySQL 技术 内幕》第 7 章；《MySQL 实战 45 讲》MVCC 讲次

### 18. 快照读与当前读的区别？
- **简答**：普通 select 是快照读（MVCC 无锁）；select...for update / update / delete 是当前读（读最新已提交版本并加锁）。
- **深答**：当前读加什么锁：RR 下主键等值命中加记录锁；范围条件加临键锁（记录+间隙）阻止插入。快照读与当前读混用会产生「读到自己快照里没有的行」的错觉——RR 下幻读「基本解决」但不是绝对（先快照读后当前读的经典反例）。这也是「for update 语义要清楚」的原因。
- **来源**：《MySQL 实战 45 讲》；MySQL 官方手册 Locking Reads

### 19. InnoDB 有哪些锁？
- **简答**：行级：记录锁、间隙锁、临键锁、插入意向锁；表级：意向锁（IS/IX）、MDL 元数据锁、AUTO-INC 锁。
- **深答**：间隙锁锁的是区间防止插入（RR 防幻读核心）；临键锁=记录+前间隙。意向锁表意「表内有行锁」，让表锁判断不用逐行扫。MDL 保护查询期间结构不被 DDL 破坏——「线上 DDL 卡死」的经典原因就是长事务持有 MDL 读锁，DDL 拿不到写锁且堵塞后续所有查询。死锁处理：等待图检测，回滚代价小者，报 1213 错误。
- **来源**：MySQL 官方手册 InnoDB Locking；《MySQL 技术 内幕》第 6 章

### 20. 什么是幻读？InnoDB 怎么防的？还有什么缝隙？
- **简答**：同事务两次同条件读行数不同；快照读靠 MVCC、当前读靠临键锁；缝隙在「先快照读后当前读」的混用。
- **深答**：经典反例：事务 A 先 select（快照，无该行）→ 事务 B insert 提交 → 事务 A update 同条件（当前读，能更新到 B 的行）→ 再 select（快照里因自己 update 过而可见）→ 出现「幻影行」。结论：RR 不是绝对无幻读，要严格一致需全程当前读（for update）。能把这个反例讲全的候选人不多了。
- **来源**：《MySQL 实战 45 讲》幻读讲次；MySQL 官方手册

### 21. 长事务有什么危害？
- **简答**：undo 无法清理（版本链膨胀+空间涨）、MDL 阻塞 DDL、主从延迟、锁持有时间拉长死锁概率上升。
- **深答**：RR 下长事务的 ReadView 一直有效：它开始后所有已删旧版本都得为它保留——undo 表空间膨胀、查询越来越慢（版本链越走越长）。排查：`information_schema.innodb_trx` 按 trx_started 排序；预防：业务禁超长交互事务、监控 trx_duration、autocommit 语义明确。这是「知道 MVCC 原理后能落地运维」的体现。
- **来源**：《MySQL 实战 45 讲》长事务讲次；MySQL information_schema 文档

### 22. 两阶段提交为什么必须？
- **简答**：让 redo 与 binlog 一致：先 redo prepare、再写 binlog、再 redo commit，崩溃后按两者对齐恢复。
- **深答**：反证：先 redo 后 binlog——binlog 没写完崩溃则主库已恢复数据但从库没有（不一致）；先 binlog 后 redo——redo 没写完崩溃则从库多了不存在的事务。两阶段提交以 redo 的 prepare/commit 为协调点，崩溃恢复时校验「redo prepare 且 binlog 完整→提交，否则回滚」。内部 XA 思想，与分布式 XA 的 2PC 同构——跨题呼应 44。
- **来源**：《MySQL 实战 45 讲》；MySQL 官方手册 Internal XA

### 23. 分布式事务方案概览：2PC/TCC/SAGA/本地消息表？
- **简答**：2PC 强一致阻塞；TCC 业务两阶段（try/confirm/cancel）；SAGA 长事务补偿；本地消息表+最终一致最实用。
- **深答**：互联网主流是「避免分布式事务」：能在一个库一个事务里做的绝不拆；跨服务用本地消息表（业务与消息同一本地事务写入，后台投递+幂等消费）或事务消息（RocketMQ）。TCC 适合资金类（要业务实现 try 预留），SAGA 适合长流程（补偿要可逆）。答题框架：一致性等级（强/最终）×复杂度×吞吐 三维权衡。
- **来源**：《微服务设计》需复核；RocketMQ 官方事务消息文档

### 24. 乐观锁与悲观锁在业务里怎么落地？
- **简答**：悲观：select...for update 先锁再改；乐观：version 列 `update ... set v=v+1 where id=? and v=?`，失败重试。
- **深答**：乐观锁零 DB 锁、适合低冲突高并发（库存扣减读多写少场景慎重——高冲突时重试风暴反而差）；悲观锁适合冲突高、临界区短。库存扣减的实战组合：原子 SQL（`stock=stock-1 where stock>0`）本质是 DB 行锁兜底的乐观语义，天然防超卖。W6 无库存场景，但这个模式与工具调用的「校验-执行」竞态同构。
- **来源**：MySQL 官方手册 Locking Reads；业务实践（需复核具体博客出处可不引）

## 四、SQL 与优化（8 题）

### 25. EXPLAIN 重点看哪些列？
- **简答**：type（访问类型）、key/key_len（实际索引）、rows（预估扫描行）、Extra（Using index/filesort/temporary 等）。
- **深答**：type 从优到差：const/eq_ref/ref/range/index/ALL——出现 ALL 且 rows 巨大即全表扫；Extra 红灯：Using filesort（排序没吃到索引）、Using temporary（临时表，常见于 distinct/group by 无索引）。分析口诀：「行数对不对、索引用没用、排序临表有没有」。8.0 用 `EXPLAIN ANALYZE` 能看到真实执行耗时树，比估算更可信。
- **来源**：MySQL 官方手册 EXPLAIN Output Format；《高性能 MySQL》第 6 章

### 26. 慢查询定位与治理流程？
- **简答**：慢日志收集→pt-query-digest 聚合→按总耗时排序逐条 EXPLAIN→索引改写或 SQL 改写→压测回归。
- **深答**：治「最大总量」而非「单条最快」：慢日志按 Query_time 聚合后，先改扫表次数最多的。改写三板斧：索引补齐、select * 砍列（配合覆盖索引）、大分页优化（`where id>last_id limit n` 游标分页替代 `limit 100000,20`——后者要扫过前 10 万行）。设 long_query_time=1 起步，优化后收紧。
- **来源**：《高性能 MySQL》第 3、6 章；Percona pt-query-digest 文档

### 27. 大分页为什么慢？怎么优化？
- **简答**：limit 100000,20 要取回前 100020 行丢弃；优化：游标分页（记住上页末 id）、延迟关联（先用覆盖索引拿 id 再回表）。
- **深答**：延迟关联写法：`select t.* from t join (select id from t where x=? order by id limit 100000,20) tmp on t.id=tmp.id`——子查询全在索引内完成只回表 20 次。游标分页最彻底但跳页不支持（产品交互上用「下一页」而非页码）。搜索场景直接上 ES/搜索引擎——「数据库不擅长它不擅长的事」。
- **来源**：《高性能 MySQL》分页小节；实践通用（可引 Google「keyset pagination」需复核）

### 28. count(*) / count(1) / count(列) 的区别？
- **简答**：count(*)≈count(1)（优化器同路径，选最小索引）；count(列) 统计非 NULL 行数且不能走最优化路径。
- **深答**：MyISAM 免 where 的 count 是 O(1)（存了行数），InnoDB 因 MVCC「每个事务看到的行数不同」必须真扫——这是面试能讲出 MVCC 深度的钩子。大表计数方案：缓存计数（定时/增量）、explain rows 估算、信息表汇总。Redis 计数器+异步对账是业务常用法。
- **来源**：《MySQL 实战 45 讲》count 讲次；MySQL 官方手册

### 29. join 的实现原理与优化？
- **简答**：Nested-Loop 为主：小表驱动大表，被驱动表连接列必须有索引；8.0 有 hash join 兜底无索引场景。
- **深答**：Block Nested-Loop 用 join buffer 攒块减少外层扫描次数；8.0.18 起 hash join 替代 BNL（等值 join 无索引时内存建哈希表）。优化原则：驱动表=过滤后行数少的一方（optimizer 一般自己选，可用 straight_join 干预）；join 列字符集/类型一致（隐式转换失效）；避免 join 后再 where 的大中间结果。业务侧「能拆就拆」：应用层两次查询+内存拼接在分布式场景（分库后 join 失效）反而是标配。
- **来源**：MySQL 8.0 官方手册 Hash Joins；《高性能 MySQL》第 6 章

### 30. 什么是半同步复制与主从延迟的成因和缓解？
- **简答**：异步复制主不等待从；半同步等至少一个从收 binlog 才回客户端；延迟成因：从库单线程重放/大事务/机器差；缓解：并行复制、拆大事务、读走从但关键读走主。
- **深答**：8.0 的 WRITESET 并行复制按行冲突集并行重放，大幅缩小延迟。读写分离的坑：写后立即读走主（会话粘性/GTID 等待 GTID executed 才返回）——「刚下单查不到订单」即此类。monitor：Seconds_Behind_Master 只是估算，用时间戳差值更准。
- **来源**：MySQL 官方手册 Replication（Semi-Synchronous、Replication Parallel Applies）；《MySQL 实战 45 讲》主从篇

### 31. 什么是 MGR / InnoDB Cluster？与主从的区别？
- **简答**：MGR 基于 Paxos 的多主/单主复制组，自动故障转移与强一致提交（多数派），是 MySQL 官方高可用方案。
- **深答**：主从异步复制故障切换可能丢数据；MGR 要求事务在多数派节点持久化才提交，天然 RPO=0（配合多数派），代价是写吞吐受限与运维复杂度。答题定位：知道「官方 HA 演进线：异步→半同步→组复制」，多数公司实际仍用「主从+orchestrator/MHA+VIP」或云 RDS 高可用版，能说出这个现实比背概念更值钱。
- **来源**：MySQL 官方手册 Group Replication

### 32. order by 的工作机制？什么时候出现 filesort？
- **简答**：走索引序直接输出；否则取数据到 sort_buffer 排序（单路全字段/双路 rowid 回表），超限用临时文件多路归并。
- **深答**：优化点：让排序列进索引（联合索引把 order by 列放等值条件后）；sort_buffer 装不下就外部归并（呼应 OS 外部排序题 43）；`max_length_for_sort_data` 决定单/双路策略。深分页+order by 是双重杀手，见 27 题。EXPLAIN 出现 filesort 不是一定慢（内存排序很快），rows 才是量级判据。
- **来源**：MySQL 官方手册 ORDER BY Optimization；呼应 os_50.md 题 43

## 五、日志、恢复与备份（5 题）

### 33. 崩溃恢复的过程？
- **简答**：重启后扫描 redo log：已 commit 的重放（前滚），未 commit 的按 undo 回滚（后滚），保证已提交不丢未提交不存在。
- **深答**：checkpoint 记录了哪些页已刷盘，恢复只重放 checkpoint 之后的 redo——WAL 的价值兑现。恢复时长与「redo 量/checkpoint 频率」相关，这也是不能把 redo 设太小的原因（太小→频繁强制 checkpoint→随机刷盘风暴）。双一配置（sync_binlog=1, innodb_flush_log_at_trx_commit=1）是金融级持久性基线。
- **来源**：《MySQL 实战 45 讲》；MySQL 官方手册 InnoDB Crash Recovery

### 34. 误删数据怎么恢复？（时间点恢复）
- **简答**：最近全量备份+重放增量 binlog 到误操作前一刻；前提 binlog 完整（row 格式+合理保留期）。
- **深答**：流程：恢复备份实例→用 binlog 定位误操作 GTID/时间点→重放到误操作前→导出受影响表回灌生产。预防优于补救：最小权限、sql_safe_updates、高危语句双人复核、延迟从库（延迟 1h 的从库是「数据时光机」）。能答出「延迟从库」这个方案的候选人很少。
- **来源**：MySQL 官方手册 Point-in-Time Recovery；percona tools 文档

### 35. 备份方案怎么设计？（全量+增量+验证）
- **简答**：定期全量（xtrabackup 物理热备）+binlog 增量+异地多副本；核心是**恢复演练**——没验证过的备份等于没有。
- **深答**：xtrabackup 物理备份大库快（拷贝文件+应用日志）；mysqldump 逻辑备份小库灵活可跨版本。RTO/RPO 双指标定方案：RPO≤5 分钟=binlog 实时归档；RTO 短=物理备份+定时演练脚本。考点：备份文件也要加密与权限管理（含敏感数据的备份泄露=裸奔）。
- **来源**：Percona XtraBackup 官方文档；MySQL 官方手册 Backup and Recovery

### 36. 表结构变更（DDL）的线上怎么做？
- **简答**：8.0 很多 DDL 支持 INSTANT/在线 DDL，但大表/长事务风险仍在；稳妥用 gh-ost/pt-osc 影子表拷贝+双写切换。
- **深答**：风险点：MDL 互斥（长事务堵 DDL 堵全表，见 19 题）、磁盘翻倍、主从延迟放大。gh-ost 用 binlog 同步到幽灵表可暂停/限流可回滚，是大表变更标准工具。流程纪律：先在从库演练、低峰执行、变更窗口+回滚预案。8.0 INSTANT 加列秒完成是版本红利，但要确认当前版本支持范围。
- **来源**：MySQL 8.0 官方手册（Instant DDL）；gh-ost 官方文档

### 37. 什么是 AHI（自适应哈希索引）？
- **简答**：InnoDB 自动对热点页的等值查询建内存哈希，免 B+树逐层下降；自动管理不可人工干预。
- **深答**：监控 show engine innodb status 的 AHI 段；高并发等值点查受益明显。争议点：极端高并发下 AHI 的读写锁竞争可能成为瓶颈，某些场景（大量非等值）反而负收益，8.0 后可在实例级关闭。答出「自动优化也有负收益、要监控」体现工程判断。
- **来源**：《MySQL 技术 内幕》第 5 章；MySQL 官方手册 Adaptive Hash Index

## 六、InnoDB 细节与工程实践（8 题）

### 38. buffer pool 的机制与调优？
- **简答**：数据页缓存区（默认 128M，生产调大到物理内存 50-70%），LRU 变体分 young/old 子链防全表扫污染。
- **深答**：innoDB LRU 新页先入 old 头（1/8 处），停留超 innodb_old_blocks_time（默认 1000ms）再被再次访问才升 young——一次性扫描（备份/大查询）不冲击热数据，这是「操作系统 LRU 思想+业务防御」的结合（呼应 OS 题 10/22）。监控：命中率高≠健康，要看 free 页与脏页比例、read ahead 是否滥用。
- **来源**：MySQL 官方手册 InnoDB Buffer Pool；《MySQL 技术 内幕》第 2 章

### 39. 脏页刷新与「抖一下」的原因？
- **简答**：checkpoint 推进需要刷脏页；redo 快满/内存不足时触发激烈刷新，前台查询被拖慢出现周期性毛刺。
- **深答**：刷脏策略：redo 追不上时强制 checkpoint（最凶）、buffer pool 不足时 LRU 回收脏页、后台空时慢刷。监控：innodb_buffer_pool_pages_dirty、checkpoint age。缓解：加大 redo、均衡写入、SSD 提升随机写（呼应 OS 题 23）。线上「每几分钟 RT 飙一下」先查这里。
- **来源**：《MySQL 实战 45 讲》刷脏页讲次；MySQL 官方手册

### 40. doublewrite buffer 是干什么的？
- **简答**：防「部分写失效」：脏页先写共享表空间两份，再写真正位置；页 16K 大于原子写单位时防撕裂页。
- **深答**：磁盘原子性通常 512B/4K，16K 页断电可能写一半——redo 按物理修改记录也可能对半页无效。doublewrite 先顺序写副本（可恢复）再写目标。SSD/文件系统支持原子写的场景可关闭省一倍写放大（如 FusionIO）。答出「页级原子性为什么是数据库的命门」是深度信号。
- **来源**：MySQL 官方手册 Doublewrite Buffer；《MySQL 技术 内幕》

### 41. 表空间与段/区/页的层次？
- **简答**：表空间→段（索引）→区（1MB/64 页）→页（16KB）→行；数据按页管理，区给顺序分配减少碎片。
- **深答**：行的物理组织（变长字段、NULL 位图、溢出页）决定「为什么 varchar 很长会行外溢出」；紧凑行格式（DYNAMIC）把长文本放溢出页，页内存 20 字节指针——这解释了「列里塞大文本拖累查询」的底层原因：一页放不下几行，缓存命中率崩。大文本应放对象存储+表存引用。
- **来源**：《MySQL 技术 内幕》第 4 章；MySQL 官方手册 InnoDB Page Structure

### 42. utf8mb4 与 utf8 的区别？emoji 报错为什么？
- **简答**：MySQL 的 utf8 是残缺 3 字节实现；utf8mb4 才是完整 UTF-8（4 字节含 emoji），MySQL 8.0 默认即 utf8mb4。
- **深答**：历史坑：5.7 建库默认 utf8（mb3），插入 emoji 报 Incorrect string value。连带坑：连接串、客户端、表列、库四层字符集要一致（就近覆盖），collation 影响排序与唯一约束（utf8mb4_0900_ai_ci vs general_ci 大小写敏感差异）。面试变体：「已线上表怎么改」——alter convert 或导出重建+双写验证，属 DDL 题 36 范畴。
- **来源**：MySQL 8.0 官方手册 Character Sets；实践通用

### 43. 分库分表的时机与代价？
- **简答**：单表数据/写入量超过单机承载（经验量级千万行/QPS 千级再谈）才分；代价：跨片查询/join/事务全变难。
- **深答**：分片键选择=最高频查询维度（如 user_id），hash 分片均匀但扩容难，range 易扩容但热点；扩容方案：双写迁移/一致性哈希。跨片难题清单：分布式 ID（雪花）、跨片 join（冗余字段/应用层拼）、跨片事务（本地消息表，呼应 23）、跨片分页（禁止跳页或聚合层归并）。先垂直拆（按业务拆库）后水平拆，且能用「归档冷数据+索引优化」顶住就别拆。
- **来源**：《高性能 MySQL》扩展篇需复核；ShardingSphere 官方文档

### 44. 为什么 W6 的记忆库用 SQLite 而不是 MySQL？边界在哪？
- **简答**：单机单进程、低写入、零运维的场景 SQLite 零成本足够；MySQL 的价值在多客户端并发、海量数据、主从扩展。
- **深答**：SQLite 是进程内嵌入式库（文件即库），W6 的会话记忆只有单 uvicorn 实例读写，SELECT/INSERT 频率低——引入 MySQL 徒增部署成本。边界：多 worker 并发写（文件锁竞争）、高并发读、需要网络访问/HA 时应迁移 MySQL/PostgreSQL。W6 v1.7 多 worker 部署时若共享记忆库，就要评估这个迁移点（或仍单实例+连接池）。「按规模选库」的答题示范。
- **来源**：SQLite 官方文档（Appropriate Uses For SQLite）；W6 w6_hr_policy/app/main.py 实现注释

### 45. 什么是最左匹配下的「索引条件下推」与「MRR」？
- **简答**：ICP 见题 9；MRR 把二级索引命中的主键排序后批量回表，把随机读变接近顺序读。
- **深答**：MRR（Multi-Range Read）：collect 主键→buffer 排序→按主键序回表，减少缓冲池页抖动；EXPLAIN 出现 Using MRR。适合范围查询大量回表的场景，但排序本身有成本，优化器按成本开关（optimizer_switch）。与 IO 题呼应：这是「数据库在引擎层做 IO 调度」的实例。
- **来源**：MySQL 官方手册 Multi-Range Read Optimization

### 46. 什么是 AHI 之外的查询优化器成本模型？统计信息如何影响选索引？
- **简答**：优化器按 IO/CPU/Mem 成本估算选计划；依赖统计信息（索引基数 cardinality），过期统计导致选错索引。
- **深答**：innodb_stats_persistent 常驻统计，采样页数（n_tiles）影响精度；大 DML 波动后 `ANALYZE TABLE` 手动刷新。症状：同 SQL 忽快忽慢、计划漂移——排查顺序：统计信息→参数影响（如 eq_range_index_dive_limit 跳过 dive 改用统计估算）。8.0 的直方图（histogram）帮非索引列估算。答出「计划漂移」这个词就有运维味。
- **来源**：MySQL 8.0 官方手册 Optimizer Statistics/Histograms

### 47. SQL 注入原理与防御？
- **简答**：拼接 SQL 让数据变代码；防御：参数化查询/ORM 绑定、最小权限、输入校验、ORM 不拼原生字符串。
- **深答**：本质是「数据与代码边界被打破」。参数化把用户输入永远当数据（预编译占位符）；ORM（SQLAlchemy/MyBatis #{}）默认绑定，但原生拼接接口（MyBatis ${}）仍是雷区。纵深：DB 账号最小权限（应用账号禁 DDL/DROP）、错误信息不回显 SQL、WAF 兜底。W6 的工具参数同样走 schema 校验+白名单，思想一致（注入面收窄）。
- **来源**：OWASP SQL Injection Prevention Cheat Sheet；MySQL 官方手册（Prepared Statements）

### 48. 如何设计一张高并发订单表的核心索引？
- **简答**：主键雪花/自增；唯一索引保证幂等（user_id+out_trade_no）；查询维度联合索引（user_id+create_time）+状态列按查询需要。
- **深答**：设计推演：①幂等：业务单号唯一索引兜底重复支付；②「我的订单」按 user_id+create_time 倒序 → 联合索引免 filesort（可把 id 冗余排序尾部）；③后台按状态筛 → (status, create_time) 但注意 status 选择性低，可加时间条件配合；④冷热分离：已完结订单归档，主表小索引才高效。答题时画出每条查询对应的索引命中路径，即「索引即查询」的设计观。
- **来源**：《高性能 MySQL》索引设计章节；业务实践综合（开源电商 schema 需复核不引）

### 49. 什么是延迟关联、什么是索引冗余的自动发现？
- **简答**：延迟关联见 27 题；冗余索引发现用 sys.schema_redundant_indexes/unused_indexes + 长周期监控。
- **深答**：实操口径：unused_indexes 要跨业务周期（月促/季末）观察再删；redundant 的经典误判是 (a,b) 与 (b,a) 各有用途（分别服务不同 where 序），不是互斥冗余。删除流程：先 invisible（8.0 不可见索引，优化器忽略但维护保留）观察一周再真删——可快速回滚的删除才是生产级删除。
- **来源**：MySQL sys schema 文档；MySQL 8.0 官方手册 Invisible Indexes

### 50. MySQL 与 Redis 的数据一致性（缓存一致性）怎么做？
- **简答**：常用 Cache-Aside：读→缓存缺失回源回填；写→先更新 DB 再删缓存（而非更新缓存）；配合过期时间兜底。
- **深答**：为什么删缓存不更新缓存：并发写时序交错会把旧值写回（写覆盖竞争），删除让下次读回源最简单。残留窗口：读旧值-写新库-删缓存-读回填旧值的极小概率交错，用延迟双删/订阅 binlog（Canal）异步删强化。强一致场景别用缓存（直接锁 DB）；能接受毫秒级不一致再上缓存——「一致性与性能的交易」思维。呼应 redis_50 题 31。
- **来源**：《MySQL 实战 45 讲》相关讨论；Cache-Aside 模式（Microsoft 云设计模式文档需复核）；呼应 redis_50.md 题 31

---

## 附：来源标注说明
- 同 network_50.md：《高性能 MySQL》《MySQL 技术 内幕》《MySQL 实战 45 讲》与 MySQL 8.0 官方手册均可核查；标「需复核」处核实后再引用。
- 与 W6/OS/Redis 的跨题呼应（18/19/22/23/32/44/48/50）已在题内标注，面试时串起来讲。
