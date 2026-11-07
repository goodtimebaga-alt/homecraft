# Homecraft

**中文** · [English](README.en.md)

## 个人网站即我的世界

过去我是个喜欢折腾网站的人，但模板换了又换，总感觉被什么东西困住了。

受我的世界、黑客帝国和元宇宙的启发，借助 AI，我把个人网站从二维网页建成了三维世界。

这个世界包罗万象，可以自由移动，里面建了篮球场，健身房，工作台，甚至还有昼夜交替和天气系统。

对于二维网页也完全可以内嵌进来，例如按 F 查看。而且得益于方块风的性能开销小，手机也能轻松访问。

逛上一圈，像是去朋友家做客了一趟。比起传统的网站，这样的相识或许更让人印象深刻。

一旦接受了这个设定，就再也回不去传统个人网站了…

## 实机截图 [🔗 Terry's Home](https://terryhu.cn)

<p align="center"><img src="docs/images/cover.webp" width="420" alt="封面"></p>

| 篮球场 | 泳池 | 工作台 |
| :---: | :---: | :---: |
| <img src="docs/images/terry-court.webp" width="240" alt="篮球场"> | <img src="docs/images/terry-pool.webp" width="240" alt="泳池"> | <img src="docs/images/terry-desk.webp" width="240" alt="工作台"> |
| **作品展示** | **健身房** | **天气系统** |
| <img src="docs/images/terry-works.webp" width="240" alt="作品展示"> | <img src="docs/images/terry-gym.webp" width="240" alt="健身房"> | <img src="docs/images/terry-snow.webp" width="240" alt="下雪"> |

## 开始使用

<p align="center"><img src="docs/images/starter.webp" width="640" alt="初始模板"></p>

一行命令 `python3 tools/serve.py`即可运行。项目已内置初始模板、相关提示词与约束。

Terry's Home 完整实现见 [examples/terry-home](examples/terry-home)。

后续更新见[更新指引](engine/UPDATING.md)。

## 匿名多人访问（可选）

本分支支持小规模匿名实时访问：游客可以在同一个空间中看到彼此的位置、朝向和基本移动状态，无需注册。多人功能默认关闭，需要自行部署 WebSocket 服务、配置反向代理，并在 `home.config.js` 中设置 `multiplayer: { enabled: true }`；服务不可用时仍可单人游览。

此功能不包含聊天，也不会同步宠物、天气或页面内容。部署方法、安全配置与使用限制详见[多人功能文档](backend/multiplayer/README.md)。
