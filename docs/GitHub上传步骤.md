# 上传 GitHub 开源共享

只上传 `github开源版` 这个整理后的目录，或解压 `chemdraw-zh-patch-v0.2.6-source.zip` 后的 `chemdraw-zh-patch` 目录。不要上传上一级原项目或旧完整发布包。

## 网页上传

1. 登录 GitHub，点击右上角 **+ → New repository**。
2. 推荐仓库名 `chemdraw-zh-patch`，简介 `Free and open-source Chinese UI patch tools for ChemDraw 26 on Windows`，选择 **Public**。
3. 本地已有 README、LICENSE、.gitignore，创建时无需重复生成。
4. 创建仓库后选择 **uploading an existing file**，或 **Add file → Upload files**。
5. 上传整理后目录**内部的文件和文件夹**，使 README.md 和 LICENSE 出现在仓库顶层。不要仅上传源码 ZIP。
6. 填写 `Initial open-source release`，点击 **Commit changes**。如果网页无法批量处理较多差分文件，使用下面的 Git 方法。

## Git 上传

安装 Git、登录 GitHub，在整理后的源码目录打开终端。首次提交前检查暂存文件，确认没有 `baseline`、`backups`、`logs`、原厂 DLL 或 EXE。

```powershell
git init -b main
git add .
git status --short
git commit -m "Release ChemDraw Chinese patch tools v0.2.6"
git remote add origin https://github.com/你的用户名/chemdraw-zh-patch.git
git push -u origin main
```

把“你的用户名”改成实际 GitHub 用户名；若仓库名不同也要修改。Git 会通过已配置的凭据管理器或浏览器完成登录，不要把密码或令牌写进项目。如果这是已有仓库，先克隆并复制本项目文件进去，使用已有仓库的分支与远端，无需重复 git init/remote add。

## 发布下载包

1. 在仓库页面进入 **Releases → Draft a new release**。
2. 新建 tag `v0.2.6`，标题 `v0.2.6 - 通用差分汉化补丁`。
3. 说明支持版本 `26.0.0.6141 x64`、免费 MIT 项目代码、尚未全部汉化，并列出测试范围。
4. 上传 `chemdraw-zh-patch-v0.2.6-windows-x64.zip` 和 `SHA256.txt` 作为附件。
5. 当前尚未完成全部功能回归，建议勾选 **This is a pre-release**，检查附件后发布。

源码仓库与下载包分开：仓库放可审阅源码与差分；Releases 放完整解压即可运行的 CMD 安装包。未指定你的 GitHub 仓库地址和登录账户前，本地准备不会自动向网上发布。

官方参考：
- [将本地代码添加到 GitHub](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)
- [网页上传文件](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)
- [创建 Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
- [MIT 许可证范围](https://choosealicense.com/licenses/mit/)
