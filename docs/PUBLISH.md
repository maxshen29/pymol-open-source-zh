# 发布到 GitHub（安全版操作指南）

本文件说明如何把本仓库发布到**你自己的** GitHub 账号。**不要**把密码交给任何
工具或他人；GitHub 也早已不支持用账号密码推送代码。

---

## 0. 先做一件事：修改刚才泄露的密码

如果你的 GitHub 密码已经以明文形式发送过，请立刻：

1. 打开 <https://github.com/settings/security> 修改密码；
2. 打开 <https://github.com/settings/sessions> 退出所有其他会话；
3. 建议开启两步验证（2FA）。

---

## 1. 创建仓库

在 GitHub 网页端新建一个空仓库，例如：

- 名称：`pymol-open-source-zh`
- 可见性：Public（或 Private）
- **不要**勾选 “Add a README / .gitignore / license”（本仓库已有）

---

## 2. 安装 Git

Windows：<https://git-scm.com/download/win>（一路默认即可）。
安装后在 PowerShell 中确认：

```powershell
git --version
```

---

## 3. 创建令牌（Personal Access Token）

用令牌代替密码推送：

1. 打开 <https://github.com/settings/tokens?type=beta>（Fine-grained token）
2. Repository access → 只选你刚建的仓库
3. Permissions → **Contents: Read and write**
4. 生成后复制令牌（形如 `github_pat_...`），**只在本机使用**

> 注意：令牌等同密码，不要提交到仓库、不要贴到聊天工具里。

---

## 4. 推送本仓库

目标仓库：<https://github.com/maxshen29/pymol-open-source-zh>
（公开仓库，默认分支 `main`，已有一个 GitHub 自动生成的 “Initial commit”，
与上游历史无关联，所以首次推送需要 `--force`。）

**方式一：一条命令（推荐）**

```powershell
.\scripts\publish.ps1
```

脚本会自动：设置身份 → 把 `origin` 指到你的仓库（上游保留为 `upstream`）
→ `git add -A` → 提交 → 推送。git 提示输入密码时，**粘贴 Personal Access
Token**（不是账号密码）。

**方式二：手动执行**

```powershell
git config user.name  maxshen29
git config user.email maxshen29@users.noreply.github.com

git remote rename origin upstream      # 上游改为 upstream
git remote add origin https://github.com/maxshen29/pymol-open-source-zh.git

git add -A
git status --short                     # 确认没有 pymol安装包/、dist/、build/
git commit -m "PyMOL 中文版：完整中文界面与 i18n 架构"
git push -u origin HEAD:main --force
```

> 大文件提醒：`.gitignore` 已排除 `pymol安装包/`、`dist/`、`build/`。
> 便携包与 wheel 请通过 **Releases**（附件）分发，不要提交进 Git 历史。

---

## 5. 发布 Release（可选，推荐）

```powershell
# 打标签
git tag -a v0.1.0 -m "PyMOL 中文版 v0.1.0"
git push origin v0.1.0
```

然后在 GitHub 的 Releases 页面新建 Release，上传：

- `dist/pymol-3.2.0a0-cp312-cp312-win_amd64.whl`
- 便携包压缩包（把 `pymol安装包/` 打成 zip，约 800 MB，GitHub 单文件上限以内）

---

## 6. 检查清单

- [ ] 已修改泄露的密码并开启 2FA
- [ ] `git status` 中没有 `pymol安装包/`、`dist/`、`build/`、`__pycache__`
- [ ] 仓库根目录有 `LICENSE`、`NOTICE`、`THIRD-PARTY-NOTICES.md`
- [ ] `README.md`（英文）与 `README.zh-CN.md`（中文）互相链接
- [ ] 仓库描述里写明 “Based on PyMOL(TM)”（商标合规）
- [ ] 按 [`RELEASE.md`](RELEASE.md) 完成发布清理与验证
