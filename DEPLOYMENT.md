# Vercel 部署指南

## 前置要求

1. 安装 Vercel CLI:
```bash
npm i -g vercel
```

2. 确保你有以下账户：
   - Vercel 账户 (https://vercel.com)
   - PostgreSQL 数据库 (推荐使用 Supabase 或 Railway)

## 部署步骤

### 1. 环境变量配置

在 Vercel 控制台中设置以下环境变量：

- `DATABASE_URL`: PostgreSQL 数据库连接字符串
- `SECRET_KEY`: JWT 密钥 (用于用户认证)
- `FRONTEND_URL`: 前端应用URL (可选)

### 2. 本地测试部署

```bash
# 登录 Vercel
vercel login

# 部署到预览环境
vercel

# 部署到生产环境
vercel --prod
```

### 3. 自动部署

将代码推送到 GitHub 后，Vercel 会自动检测并部署：

```bash
git add .
git commit -m "准备Vercel部署"
git push origin main
```

## 数据库设置

### 使用 Supabase (推荐)

1. 访问 https://supabase.com
2. 创建新项目
3. 获取数据库连接字符串
4. 在 Vercel 环境变量中设置 `DATABASE_URL`

### 使用 Railway

1. 访问 https://railway.app
2. 创建 PostgreSQL 数据库
3. 获取连接字符串
4. 设置环境变量

## 注意事项

1. **数据库连接**: 确保使用 PostgreSQL，SQLite 在 Vercel 上不可用
2. **文件上传**: Vercel 是无状态环境，不支持本地文件存储
3. **环境变量**: 所有敏感信息都应通过环境变量配置
4. **CORS**: 已配置支持 Vercel 域名

## 故障排除

### 常见问题

1. **导入错误**: 确保所有依赖都在 `requirements.txt` 中
2. **数据库连接失败**: 检查 `DATABASE_URL` 格式和网络连接
3. **CORS 错误**: 确认前端域名在 CORS 配置中

### 查看日志

```bash
vercel logs
```

## API 端点

部署后，你的 API 将在以下地址可用：
- 生产环境: `https://your-project.vercel.app/api/`
- 开发环境: `https://your-project-git-main-your-username.vercel.app/api/` 