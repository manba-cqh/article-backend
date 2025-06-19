# Article Backend

FastAPI 后端应用，已配置 Supabase 数据库连接。

## 配置完成

✅ 数据库连接已配置 (Supabase)  
✅ JWT 密钥已设置  
✅ Vercel 部署配置已修复  

## 修复的问题

- 修复了 Vercel 运行时配置错误
- 简化了 `vercel.json` 配置
- 移除了不必要的 `api` 目录

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
2. `requirements.txt` 是否包含所有依赖
3. 数据库连接是否正常 