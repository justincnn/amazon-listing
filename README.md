# ListingGenius

## 关于
ListingGenius 是一个自托管的 Web 应用程序，旨在简化亚马逊产品列表的创建过程。用户可以输入原始产品信息，然后通过单击按钮，使用可配置的外部大型语言模型 (LLM) API 生成引人注目的标题、五个要点和完整的产品描述。

生成的内容完全可编辑，并可以保存到本地 SQLite 数据库中以供备份和将来参考。

## 功能
- **密码保护：** 安全访问应用程序。
- **AI 驱动生成：** 连接到任何兼容的 LLM API（如 Ollama）以生成列表内容。
- **可配置设置：** 通过用户界面轻松更改 API URL、API 密钥、模型名称和主提示。
- **可编辑输出：** 所有生成的字段（标题、要点、描述）都可以手动编辑。
- **本地数据库存储：** 将您的最终列表保存到持久的 SQLite 数据库中。
- **简洁、现代的用户界面：** 具有“macOS 审美”的简单、直观的界面。
- **推送部署：** 使用 GitHub Actions 构建 Docker 镜像并将其推送到 Docker Hub 的全自动 CI/CD 管道。
- **简单的生产部署：** 使用单个 `docker-compose.yml` 文件在任何 VPS 上使用 Docker 进行部署。

## 部署说明（分步指南）

请按照以下步骤部署您自己的 ListingGenius 实例。

### 1. Fork 并配置 GitHub 仓库
1.  在 GitHub 上将此仓库 **Fork** 到您自己的帐户。
2.  导航到您的新仓库的 **Settings** 选项卡。
3.  在左侧边栏中，转到 **Secrets and variables** -> **Actions**。
4.  单击 **New repository secret** 并添加以下两个密钥：
    *   `DOCKERHUB_USERNAME`：您的 Docker Hub 用户名。
    *   `DOCKERHUB_TOKEN`：您的 Docker Hub 访问令牌。您可以在 Docker Hub 帐户设置的“Security”下生成一个。

### 2. 更新占位符
您需要将两个文件中的占位符用户名替换为您的实际 Docker Hub 用户名。

1.  **编辑 `.github/workflows/docker-publish.yml`**：
    *   在第 24 行，将 `yourdockerhubusername/listinggenius` 更改为 `<YOUR_DOCKERHUB_USERNAME>/listinggenius`。
2.  **编辑 `docker-compose.yml`**：
    *   在第 5 行，将 `yourdockerhubusername/listinggenius:latest` 更改为 `<YOUR_DOCKERHUB_USERNAME>/listinggenius:latest`。

### 3. 触发首次构建
1.  对仓库中的任何文件进行少量更改（例如，在此 `README.md` 中添加一个空格）并将其推送到 `main` 分支。
    ```bash
    git commit -m "Trigger initial build" --allow-empty
    git push origin main
    ```
2.  转到您的 GitHub 仓库中的 **Actions** 选项卡。您应该会看到“Docker Image CI”工作流正在运行。等待它成功完成。这将构建您的应用程序的 Docker 镜像并将其推送到您的 Docker Hub 帐户。

### 4. 在您的 VPS 上部署
1.  **通过 SSH 登录到您的 VPS**。
2.  **为应用程序创建一个目录**。
    ```bash
    mkdir listinggenius && cd listinggenius
    ```
3.  **创建一个 `.env` 文件**。复制 `.env.example` 的内容。
    ```bash
    nano .env
    ```
    粘贴以下内容，并将 `your_secret_password` 替换为一个强大的私密密码。
    ```
    APP_PASSWORD=your_secret_password
    ```
    保存并关闭文件（在 `nano` 中，按 `Ctrl+X`，然后按 `Y`，然后按 `Enter`）。
4.  **创建 `docker-compose.yml` 文件**。
    ```bash
    nano docker-compose.yml
    ```
    粘贴您仓库中 `docker-compose.yml` 文件的内容（确保您已在其中更新了用户名）。
5.  **从 Docker Hub 拉取镜像**。
    ```bash
    docker-compose pull
    ```
6.  **启动应用程序**。
    ```bash
    docker-compose up -d
    ```
您的 ListingGenius 应用程序现在应该正在运行，并可通过 `http://<YOUR_VPS_IP>:5001` 访问。

## 使用方法
1.  打开浏览器并导航到 `http://<YOUR_VPS_IP>:5001`。
2.  输入您在 `.env` 文件中设置的 `APP_PASSWORD` 以登录。
3.  **配置设置：**
    *   单击齿轮图标打开设置面板。
    *   输入您的 LLM 提供商的 **API URL**（例如，如果在同一台机器上运行 Ollama，则为 `http://localhost:11434/api/generate`）。
    *   输入您的 **API 密钥**（如果您的提供商需要）。
    *   输入您要使用的 **模型名称**（例如 `llama3`）。
    *   如果需要，可以查看和编辑 **主提示**。默认设置已优化用于生成 JSON 输出。
    *   单击 **保存设置**。这些设置将保存在您浏览器的本地存储中。
4.  **生成列表：**
    *   将您的产品详细信息粘贴到“您的产品信息”文本区域。
    *   单击“生成列表”按钮。
5.  **编辑和保存：**
    *   根据需要修改生成的标题、要点和描述。
    *   单击“保存到数据库”以保留永久记录。
6.  **查看历史记录：**
    *   单击时钟图标以查看所有以前保存的列表。