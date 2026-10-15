// SPDX-License-Identifier: MIT
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

internal static class Program {
    internal const string ProjectUrl = "https://github.com/yangshaoxiao/chemdraw-zh-patch";
    [STAThread] static int Main(string[] args) {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        try {
            // Read-only build verification; never invokes the installer.
            if (args.Length == 2 && args[0] == "--verify-package") {
                string folder = Payload.Extract();
                File.WriteAllText(args[1], folder, Encoding.UTF8);
                return 0;
            }
            if (args.Length != 0) throw new ArgumentException("不支持的启动参数。");
            bool created;
            using (var mutex = new Mutex(true, @"Local\ChemDrawZhPatch.Gui", out created)) {
                if (!created) { MessageBox.Show("汉化工具已经打开，请使用现有窗口。", "提示"); return 0; }
                try { Application.Run(new MainForm()); } finally { mutex.ReleaseMutex(); }
            }
            return 0;
        } catch (Exception e) {
            MessageBox.Show(e.Message, "启动失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}

internal static class Payload {
    internal static string Extract() {
        byte[] bytes;
        using (Stream source = Assembly.GetExecutingAssembly().GetManifestResourceStream("patch.zip"))
        using (var memory = new MemoryStream()) { source.CopyTo(memory); bytes = memory.ToArray(); }
        using (var sha = SHA256.Create()) {
            string actual = BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
            if (actual != BuildInfo.PayloadHash) throw new InvalidDataException("内置补丁校验失败，请从 GitHub 重新下载。");
        }
        string root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ChemDrawZhPatch", "runs", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        // Refuse links/junctions in every existing ancestor before extracting executable scripts.
        for (var directory = new DirectoryInfo(root); directory != null; directory = directory.Parent)
            if ((directory.Attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("补丁工作目录不能位于符号链接或联接中。");
        string prefix = Path.GetFullPath(root) + Path.DirectorySeparatorChar;
        using (var memory = new MemoryStream(bytes))
        using (var archive = new ZipArchive(memory, ZipArchiveMode.Read)) {
            foreach (var entry in archive.Entries) {
                string destination = Path.GetFullPath(Path.Combine(root, entry.FullName));
                if (!destination.StartsWith(prefix, StringComparison.OrdinalIgnoreCase) || entry.FullName.Contains(":"))
                    throw new InvalidDataException("内置补丁路径无效。");
                Directory.CreateDirectory(Path.GetDirectoryName(destination));
                using (var input = entry.Open())
                using (var output = new FileStream(destination, FileMode.CreateNew, FileAccess.Write)) input.CopyTo(output);
            }
        }
        return root;
    }
}

internal sealed class MainForm : Form {
    readonly Button install = new Button(), restore = new Button();
    readonly Label status = new Label();
    readonly TextBox output = new TextBox();
    readonly ProgressBar progress = new ProgressBar();
    bool busy;
    string package;
    internal MainForm() {
        Text = "ChemDraw 汉化工具 · 免费开源 · v" + BuildInfo.Version;
        Font = new Font("Microsoft YaHei UI", 10F);
        AutoScaleDimensions = new SizeF(96, 96);
        AutoScaleMode = AutoScaleMode.Dpi;
        ClientSize = new Size(700, 560);
        MinimumSize = new Size(680, 560);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(247, 249, 252);
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(26), ColumnCount = 1, RowCount = 8 };
        foreach (int height in new[] { 45, 62, 80, 40, 10 }) layout.RowStyles.Add(new RowStyle(SizeType.Absolute, height));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 32));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 35));
        Controls.Add(layout);
        layout.Controls.Add(new Label { Text = "ChemDraw 中文界面", Dock = DockStyle.Fill, Font = new Font(Font.FontFamily, 21F, FontStyle.Bold) }, 0, 0);
        layout.Controls.Add(new Label { Text = "支持 ChemDraw 26.0.0.6141 x64（含 Chem3D、ChemOffice Excel）\n操作前请保存文档；确认后将自动请求相关程序正常退出。", Dock = DockStyle.Fill, ForeColor = Color.FromArgb(72, 82, 96) }, 0, 1);
        var buttons = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, Margin = new Padding(0, 5, 0, 12) };
        buttons.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50)); buttons.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        ConfigureButton(install, "汉化", Color.FromArgb(36, 99, 202), Color.White);
        ConfigureButton(restore, "还原", Color.White, Color.FromArgb(35, 52, 75));
        install.Margin = new Padding(0, 0, 8, 0); restore.Margin = new Padding(8, 0, 0, 0);
        buttons.Controls.Add(install, 0, 0); buttons.Controls.Add(restore, 1, 0); layout.Controls.Add(buttons, 0, 2);
        status.Text = "准备就绪 · 还原将恢复为英文界面"; status.Dock = DockStyle.Fill; status.TextAlign = ContentAlignment.MiddleLeft;
        layout.Controls.Add(status, 0, 3);
        progress.Dock = DockStyle.Fill; progress.Style = ProgressBarStyle.Continuous; layout.Controls.Add(progress, 0, 4);
        output.Dock = DockStyle.Fill; output.Multiline = true; output.ReadOnly = true; output.ScrollBars = ScrollBars.Vertical;
        output.BackColor = Color.White; output.BorderStyle = BorderStyle.FixedSingle; output.Margin = new Padding(0, 12, 0, 8);
        output.Text = "点击上方按钮开始。程序会自动寻找安装目录、检查版本，并在修改前备份。\r\n\r\n操作结果将在这里显示。";
        layout.Controls.Add(output, 0, 5);
        layout.Controls.Add(new Label { Text = "本补丁免费开源，无收费激活、无设备绑定。谨防付费转卖。", Dock = DockStyle.Fill, ForeColor = Color.FromArgb(139, 75, 18), TextAlign = ContentAlignment.MiddleLeft }, 0, 6);
        var link = new LinkLabel { Text = Program.ProjectUrl, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft };
        link.LinkClicked += delegate { try { Process.Start(new ProcessStartInfo(Program.ProjectUrl) { UseShellExecute = true }); } catch (Exception e) { MessageBox.Show(this, e.Message, "无法打开项目地址"); } };
        layout.Controls.Add(link, 0, 7);
        install.Click += async delegate { await Run("Install"); };
        restore.Click += async delegate { await Run("Restore"); };
        FormClosing += delegate(object sender, FormClosingEventArgs e) {
            if (busy) { e.Cancel = true; MessageBox.Show(this, "操作正在进行，请等待结果后再关闭，以免中断文件写入。", "请稍候"); }
        };
    }
    void ConfigureButton(Button button, string title, Color background, Color foreground) {
        button.Text = title; button.Dock = DockStyle.Fill; button.Font = new Font(Font.FontFamily, 16F, FontStyle.Bold);
        button.BackColor = background; button.ForeColor = foreground; button.FlatStyle = FlatStyle.Flat; button.FlatAppearance.BorderColor = Color.FromArgb(208, 217, 230);
        button.UseVisualStyleBackColor = false; button.Cursor = Cursors.Hand;
    }
    void Append(string line) {
        if (line == null || IsDisposed) return;
        if (InvokeRequired) { BeginInvoke(new Action<string>(Append), line); return; }
        output.AppendText(line + Environment.NewLine);
    }
    async Task Run(string mode) {
        if (busy) return;
        string operation = mode == "Install" ? "汉化" : "还原";
        string preparation = "执行前请完成以下操作：\r\n\r\n"
            + "1. 保存所有 Excel、ChemDraw 和 Chem3D 文档。\r\n"
            + "2. 确认后，程序将请求 Excel、ChemDraw、Chem3D 等相关窗口正常退出。\r\n"
            + "3. 确认软件版本为 ChemDraw 26.0.0.6141 x64。\r\n\r\n"
            + (mode == "Install" ? "本次操作将安装中文界面。" : "本次操作将恢复英文界面。")
            + "程序会先校验文件并保留备份。\r\n"
            + "管理员身份同样须经本次确认；未提权时还会请求系统管理员授权。\r\n\r\n"
            + "如出现未保存文档提示，请自行处理；不会强制结束进程。\r\n\r\n是否同意关闭相关程序，并确认开始" + operation + "？";
        if (MessageBox.Show(this, preparation, "执行前确认 · " + operation,
            MessageBoxButtons.YesNo, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2) != DialogResult.Yes) return;
        busy = true; install.Enabled = restore.Enabled = false; output.Clear();
        progress.Style = ProgressBarStyle.Marquee;
        status.Text = "正在检查并处理，请稍候… 如出现管理员提示，请选择“是”。";
        try {
            if (package == null) package = await Task.Run(() => Payload.Extract());
            string ps = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), @"WindowsPowerShell\v1.0\powershell.exe");
            var start = new ProcessStartInfo(ps, "-NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File \"" + Path.Combine(package, "install.ps1") + "\" -Mode " + mode + " -Gui -CloseApplications") {
                UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8, WorkingDirectory = package
            };
            int code = await Task.Run(() => {
                using (var process = new Process { StartInfo = start }) {
                    process.OutputDataReceived += (s, e) => Append(e.Data);
                    process.ErrorDataReceived += (s, e) => Append(e.Data);
                    process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine(); process.WaitForExit();
                    return process.ExitCode;
                }
            });
            status.Text = code == 0 ? (mode == "Install" ? "汉化完成，可以打开软件了。" : "还原完成，已恢复英文界面。") : "操作未完成，请查看下方原因，处理后重试。";
            status.ForeColor = code == 0 ? Color.FromArgb(20, 117, 75) : Color.FromArgb(175, 48, 42);
            Append("\r\n本次工作目录（日志与备份）：" + package);
            File.WriteAllText(Path.Combine(package, "gui-output.txt"), output.Text, Encoding.UTF8);
        } catch (Exception e) { status.Text = "操作未完成"; Append(e.Message); }
        finally { progress.Style = ProgressBarStyle.Continuous; busy = false; install.Enabled = restore.Enabled = true; }
    }
}
