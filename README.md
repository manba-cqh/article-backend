# Article Backend

FastAPI 后端应用，已配置 Supabase 数据库连接。

## 配置完成

✅ 数据库连接已配置 (Supabase)  
✅ JWT 密钥已设置  
✅ Vercel 部署配置已修复  
✅ API 目录结构已创建  
✅ 部署失败问题已解决  

## 修复的问题

- 修复了 Vercel 运行时配置错误
- 创建了正确的 `api` 目录结构
- 复制了所有必要的依赖文件到 `api` 目录
- 更新了 `vercel.json` 配置
- 简化了依赖配置，避免安装错误
- 使用更稳定的 Python 运行时版本
- 创建了简单的 `index.py` 入口文件

## 项目结构

```
article-backend/
├── api/                    # Vercel 函数目录
│   ├── index.py           # 入口文件
│   ├── server.py          # 主应用文件
│   ├── models.py          # 数据库模型
│   ├── schemas.py         # Pydantic 模式
│   ├── auth.py            # 认证模块
│   ├── database.py        # 数据库配置
│   └── requirements.txt   # Python 依赖
├── vercel.json            # Vercel 配置
└── README.md              # 项目说明
```

## 部署配置

- 使用 `@vercel/python@2.0.0` 运行时
- 入口文件: `api/index.py`
- 简化的依赖配置

## 部署到 Vercel

### 1. 安装 Vercel CLI
```bash
npm install -g vercel
```

### 2. 登录 Vercel
```bash
vercel login
```

### 3. 部署项目
```bash
# 预览部署
vercel

# 生产部署
vercel --prod
```

## API 端点

部署后，你的 API 将在以下地址可用：
- 生产环境: `https://your-project.vercel.app/api/`
- API 文档: `https://your-project.vercel.app/docs`

## 主要功能

- 用户注册/登录
- JWT 认证
- 序列号验证
- 报告管理
- Webhook 处理

## 数据库

使用 Supabase PostgreSQL 数据库，表结构会自动创建。

## 故障排除

如果遇到部署问题，请检查：
1. `vercel.json` 配置是否正确
2. `api/requirements.txt` 是否包含所有依赖
3. 数据库连接是否正常
4. 所有必要的文件是否都在 `api` 目录中
5. 入口文件 `api/index.py` 是否存在
6. 是否使用了稳定的运行时版本 