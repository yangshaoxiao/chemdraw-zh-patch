# ChemDraw 简体中文扩展补丁

免费、开源的 Windows ChemDraw 界面汉化工具。当前翻译覆盖 78 个文件、5974 处文字替换。v0.2.1 改进安装路径识别与差分发布方式，中文内容与本机验证过的 v0.2 一致。

**当前支持 ChemDraw 26.0.0.6141 x64。尚未实现整个软件全部汉化。** 没有电脑数量限制，可复制到多台已正确安装同一受支持版本的电脑使用。其他版本、Mac、缺失组件或其他补丁修改过的文件不会被视为兼容安装。

## 安装与还原

1. 下载 Releases 中的 `ChemDraw26_中文补丁_v0.2.1_通用差分版.zip`，完整解压到可写目录。也可以在仓库页面选择 **Code → Download ZIP**，完整解压源码包后直接运行下面的 CMD 文件。
2. 保存文档并关闭 ChemDraw，双击 `一键安装汉化.cmd`。
3. 安装器自动查询标准安装目录与注册表。找不到安装时，按提示粘贴含 `ChemDraw.exe` 的文件夹路径。默认数据目录来自 Windows 的 ProgramData；若数据安装在其他位置，按提示填写含 `GUI` 的数据目录。
4. Windows 弹出管理员权限提示时选择“是”。显示全部文件校验通过后启动 ChemDraw。

还原：关闭 ChemDraw，运行 `一键还原英文.cmd`。只检查：运行 `检查安装环境.cmd`。

普通用户不需要 Python、Git 或下载运行库；安装器使用 Windows 自带 PowerShell 5.1 和 .NET。需要使用账户具备管理员提权能力。

在受限环境或自定义安装中，可以明确指定目录：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Mode Install -BinPath "D:\ChemDraw\ChemDrawApplications_x64" -DataPath "D:\ChemDrawData\ChemDraw"
```

## 文件保护

安装前检查程序版本、x64 架构、每个目标文件和差分数据的 SHA-256。所有待写入文件重建并校验后，才开始修改安装目录。未知文件修改会拒绝覆盖。支持英文原版、此项目 v0.1 和 v0.2 的已知文件状态；已完成的安装会跳过重复处理。

执行前状态保存在解压目录的 `backups/`，运行记录在 `logs/`。中途写入失败时尝试回滚到执行前状态。差分包包含从已知汉化状态恢复英文所需的反向差分，正常还原不需要下载原厂文件。

**不要把执行后的 backups、logs、完整 DLL 或原始软件文件上传到 GitHub。** 新发布包不包含完整的软件 EXE/DLL 或本机绝对路径。

## 覆盖与局限

替换次数：XML 2044、原生对话框 1647、字符串资源 2131、ChemACX 插件 13、托管界面 139。数字不是独立词条数或覆盖百分比。

仍有英文：动态生成的 Search、Add-ins 等菜单和标题、部分首选项分类与表格状态、在线插件说明、模板内部名称，以及尚未确认运行时编码的自定义资源。化学数据、外部网站和 PDF 手册未全面翻译；个别短标签仍需调整布局。

真实机器已完成 v0.2 安装、启动和部分设置/插件窗口检查。v0.2.1 的安装和还原测试采用隔离目录，详细结果见 `docs/verification_report.json`。尚未进行全部绘图、计算、打印、云服务和模块回归测试。

## 开源与开发

本项目免费提供，原创内容采用 MIT。ChemDraw 的商业授权和第三方权利保持各自范围，详见 [NOTICE.md](NOTICE.md) 和 [LICENSE](LICENSE)。

开发流程见 [docs/开发与发布.md](docs/开发与发布.md)，GitHub 上传步骤见 [docs/GitHub上传步骤.md](docs/GitHub上传步骤.md)。欢迎提交界面翻译修正、兼容版本测试及控件布局改进。
