# DBVault 前端设计规范

本文档沉淀 DBVault 当前前端的可复刻设计语言，用于在其他项目中快速复制同类企业后台体验。

## 设计定位

DBVault 的前端设计语言可以概括为：**Slate/Blue 企业运维控制台**。

它不是营销型界面，而是面向数据库备份、恢复、审计、告警等运维场景的高密度后台系统。视觉重心放在数据、状态和操作效率上，装饰克制，层级清晰。

适合复刻到：

- SaaS 管理后台
- DevOps / 平台工程控制台
- 数据库、存储、备份、安全、监控类系统
- 多资源、多状态、多操作的企业内部工具

不建议直接复刻到：

- 品牌官网
- 内容资讯站
- 强营销落地页
- 需要强沉浸视觉表达的 C 端产品

## 技术基底

推荐技术栈：

- Vue 3
- Vite
- Element Plus
- `@element-plus/icons-vue`
- ECharts
- Pinia
- Vue Router
- Vue I18n
- Day.js

设计复刻的关键不是框架本身，而是保持 Element Plus 组件体系、全局 CSS token、统一布局骨架和业务页面模板一致。

## 色彩系统

核心配色是 slate 灰蓝底色 + blue 主色 + 语义状态色。

### Light Theme

| Token | Color | 用途 |
| --- | --- | --- |
| `--bg-color` | `#f8fafc` | 页面底色 |
| `--bg-color-mute` | `#f1f5f9` | 表头、输入框、hover 背景 |
| `--card-bg` | `#ffffff` | 卡片、弹窗、表格背景 |
| `--text-color` | `#0f172a` | 主标题、正文 |
| `--text-muted` | `#64748b` | 辅助文字、说明、弱信息 |
| `--border-color` | `#e2e8f0` | 卡片、表格、弹窗分割线 |
| `--primary` | `#2563eb` | 主按钮、主强调 |
| `--primary-hover` | `#3b82f6` | 主色 hover |
| `--success` | `#10b981` | 成功、可用、完成 |
| `--warning` | `#f59e0b` | 运行中、警告、中风险 |
| `--danger` | `#ef4444` | 失败、删除、高风险 |

### Dark Theme

| Token | Color | 用途 |
| --- | --- | --- |
| `--bg-color` | `#020617` | 页面底色 |
| `--bg-color-mute` | `#0f172a` | 弱背景 |
| `--card-bg` | `#1e293b` | 卡片、弹窗 |
| `--text-color` | `#f8fafc` | 主文字 |
| `--text-muted` | `#94a3b8` | 辅助文字 |
| `--border-color` | `#334155` | 分割线 |
| `--primary` | `#3b82f6` | 主色 |
| `--primary-hover` | `#60a5fa` | 主色 hover |

### Sidebar Theme

侧边栏使用独立的深色体系，让导航区域形成稳定的产品框架。

| Token | Color | 用途 |
| --- | --- | --- |
| `--sidebar-bg` | `#0f172a` | Light 模式侧边栏 |
| `--sidebar-bg` dark | `#020617` | Dark 模式侧边栏 |
| `--sidebar-text` | `#94a3b8` | 默认菜单文字 |
| `--sidebar-active-bg` | `#1e293b` | 当前菜单背景 |
| `--sidebar-active-text` | `#38bdf8` | 当前菜单文字 |

### 颜色使用规则

- 蓝色只用于主操作、当前导航和关键强调。
- 绿色只表达成功、可用、完成。
- 黄色只表达运行中、等待确认、风险预警。
- 红色只表达失败、删除、禁用、高风险告警。
- 灰蓝色承担背景、边框和辅助信息，不额外增加装饰色。
- 不使用大面积彩色渐变作为业务页面背景。

## 字体与字号

字体栈：

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
```

推荐字号：

| 场景 | 字号 | 字重 | 说明 |
| --- | ---: | ---: | --- |
| 页面标题 | `20px` | `700` | 顶栏当前页面标题 |
| 卡片标题 | `16px` | `600` | 卡片 header 标题 |
| 表头 | `12px` | `600` | 大写，字距 `0.5px` |
| 正文/表格 | `14px` | `400-500` | 主要数据文本 |
| 辅助说明 | `12-13px` | `400` | role、说明、弱数据 |
| 指标标签 | `14px` | `600` | 大写，字距 `0.5px` |
| 指标数字 | `32px` | `700` | Dashboard 统计卡 |
| 登录主标题 | `48px` | `800` | 仅登录页左侧品牌区 |
| 登录表单标题 | `32px` | `700` | 登录表单区 |

## 布局骨架

主应用采用固定后台布局：

- 左侧侧边栏：`260px`
- 顶部 header：`70px`
- 内容区 padding：`30px`
- 内容区背景：`var(--main-bg)`
- 页面内容直接进入数据工作区，不做营销 hero

结构规则：

1. 左侧侧边栏放品牌和一级导航。
2. Header 左侧显示当前路由标题。
3. Header 右侧放主题切换、用户头像、用户菜单。
4. 主内容区只放当前页面业务内容。
5. 页面切换使用轻量淡入和垂直位移。

## 侧边栏规范

侧边栏是产品识别和导航中心。

尺寸与样式：

- 宽度：`260px`
- Logo 区高度：`80px`
- Logo 区左右 padding：`24px`
- 菜单容器 padding：`10px`
- 菜单项高度：`48px`
- 菜单项圆角：`8px`
- 菜单项间距：`4px`
- 菜单项字重：`500`

交互规则：

- 当前菜单项使用 `--sidebar-active-bg` 和 `--sidebar-active-text`。
- hover 背景使用 `rgba(255, 255, 255, 0.05)`。
- 每个一级入口都应配 Element Plus 图标。
- 菜单项根据权限隐藏，不显示无权限入口。

## Header 规范

Header 是上下文和账户操作区域，不承载复杂业务操作。

尺寸与样式：

- 高度：`70px`
- 背景：`var(--card-bg)`
- 底部分割线：`1px solid var(--border-color)`
- 左右 padding：`30px`
- 页面标题：`20px`、`700`

右侧组件：

- 主题切换开关
- 用户头像方块，`36px x 36px`
- 用户名，`14px`、`600`
- 角色名，`12px`、muted
- 下拉退出菜单

## 内容区规范

内容区应保持高密度但不拥挤。

- 主内容 padding：`30px`
- 栅格 gutter：`24px`
- 区块垂直间距：`24px`
- 主页面不要在卡片外再包一层视觉容器。
- 不使用卡片嵌套卡片。
- 业务页优先使用单个主卡片承载筛选、表格、分页。

## 卡片规范

卡片是业务内容的主要容器。

全局样式：

- 背景：`var(--card-bg)`
- 边框：`1px solid var(--border-color)`
- 圆角：`12px`
- 常态阴影：`0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)`
- hover 阴影：`0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)`
- header padding：`20px 24px`

使用规则：

- Dashboard 可使用多个并列卡片。
- 列表页通常只使用一个主卡片。
- 卡片 header 左侧放标题，右侧放筛选与主操作。
- 表格型卡片可以让 card body padding 为 `0`，表格贴合卡片底部。

## 表格规范

表格是系统的信息核心。

基础配置：

- 使用 `el-table`
- 默认启用 `border`
- 默认启用 `stripe`
- 常用 `size="default"`
- 宽度 `100%`
- 需要排序的列加 `sortable`
- 长文本加 `show-overflow-tooltip`
- 操作列固定右侧：`fixed="right"`

表头样式：

- 背景：`var(--bg-color-mute)`
- 字色：`var(--text-muted)`
- 字号：`12px`
- 字重：`600`
- 大写：`text-transform: uppercase`
- 字距：`0.5px`
- 上下 padding：`12px`

单元格样式：

- 上下 padding：`12px`
- 只保留底部分割线
- 移除右侧竖线强调
- hover 背景使用 `var(--bg-color-mute)`

列宽建议：

| 列类型 | 推荐宽度 |
| --- | ---: |
| ID | `80px` |
| 状态 | `100-120px` |
| 类型 | `100-140px` |
| 时间 | `160-180px` |
| 操作 | `100-220px` |
| 名称/标题 | 弹性宽度 |
| 描述/错误信息 | `min-width: 200px` + tooltip |

分页规则：

- 放在表格下方。
- 距表格 `20px`。
- 右对齐。
- `page-sizes` 使用 `[10, 20, 50]`。
- layout 使用 `total, sizes, prev, pager, next`。

## 列表页模板

所有资源管理页面优先使用同一模板：

```vue
<el-card>
  <template #header>
    <div class="card-header">
      <span>资源列表</span>
      <div class="header-filters">
        <el-input />
        <el-select />
        <el-button type="primary">
          <el-icon><Plus /></el-icon>
          新增
        </el-button>
      </div>
    </div>
  </template>

  <el-table border stripe />

  <el-pagination />
</el-card>
```

Header 筛选区规则：

- 使用 flex 横排。
- gap：`10px`。
- 输入框宽度通常 `180px`。
- Select 宽度通常 `120-180px`。
- 最右侧放主操作按钮。

## Dashboard 模板

Dashboard 用于概览，不承载复杂 CRUD。

推荐结构：

1. 第一行：4 个统计卡。
2. 第二行：主趋势图 `16/24` + 辅助占比图 `8/24`。
3. 第三行：容量/进度信息。
4. 第四行：最近备份、活跃告警等小表格。

统计卡规则：

- 卡片内 padding：`16px`
- 左侧：指标标签 + 指标值
- 右侧：图标块
- 图标块尺寸：`56px x 56px`
- 图标块圆角：`16px`
- 图标尺寸：`28px`

推荐指标色：

| 指标类型 | 主色 | 背景 |
| --- | --- | --- |
| 数据库/基础资源 | `#00d2ff` | `rgba(0, 210, 255, 0.1)` |
| 成功/备份 | `#00e676` | `rgba(0, 230, 118, 0.1)` |
| 任务/运行中 | `#ffb74d` | `rgba(255, 183, 77, 0.1)` |
| 告警/失败 | `#f1416c` | `rgba(241, 65, 108, 0.1)` |

## 图表规范

图表只用于概览和趋势判断，不做过度视觉装饰。

通用规则：

- 图表容器高度：`300px`
- legend 放底部或底部附近
- tooltip 保持默认清晰风格
- 坐标轴使用浅灰色
- 网格线使用浅色虚线

折线图：

- 平滑线：`smooth: true`
- 线宽：`3`
- 成功线：`#00e676`
- 失败线：`#f1416c`
- 可使用轻量渐变面积，透明度从 `0.3` 到 `0.05`

环图：

- 半径：`['40%', '70%']`
- 默认隐藏标签
- hover 时显示中心标签
- 扇区间使用白色 `2px` 分隔
- 存储类图表可使用青蓝渐变数组

## 表单与弹窗规范

新增、编辑、执行任务、重置密码等操作统一使用弹窗，不跳转独立页面。

弹窗样式：

- 圆角：`12px`
- 背景：`var(--card-bg)`
- header padding：`20px 24px`
- body padding：`24px`
- footer padding：`16px 24px`
- header/footer 都使用边框分割

弹窗宽度：

| 表单复杂度 | 推荐宽度 |
| --- | ---: |
| 简单确认/重置 | `500px` |
| 常规创建/编辑 | `600px` |
| 复杂数据库配置 | `680px` |
| 管理子资源/嵌套表格 | `720px` |

表单规则：

- 简单表单 label width：`100px`
- 复杂配置表单 label width：`140px`
- Select、InputNumber 在表单内通常宽度 `100%`
- 密码字段使用 `show-password`
- 条件字段通过 `v-if` 展示，不展示无关配置
- footer 左侧取消、右侧主确认

## 输入控件规范

输入框和选择器使用弱背景。

基础样式：

- 背景：`var(--bg-color-mute)`
- 默认内描边：`0 0 0 1px var(--border-color) inset`
- focus 内描边：`0 0 0 1px var(--el-color-primary) inset`
- 文本：`var(--text-color)`

登录页输入框可更大：

- 高度：`48px`
- 圆角：`8px`
- 左右 padding：`16px`
- 使用 prefix icon

## 按钮规范

全局按钮：

- 字重：`600`
- 圆角：`6px`

使用规则：

- 主操作使用 `type="primary"`。
- 删除使用 `type="danger"`。
- 需要提醒但非删除的操作使用 `type="warning"`。
- 行内操作使用 `size="small"`。
- 卡片 header 的主操作放最右侧。
- 只读跳转使用 `type="primary" link`。
- 有明确动作含义时配 Element Plus 图标，例如新增、上传、刷新。

## 状态标签规范

状态必须用 `el-tag`，不要只靠文本颜色。

通用映射：

| 状态含义 | Element Plus type |
| --- | --- |
| 成功、完成、可用、启用 | `success` |
| 运行中、警告、中风险 | `warning` |
| 失败、删除、高危、禁用、打开告警 | `danger` |
| 待处理、低风险、未知、过期 | `info` |
| 主角色/普通强调 | `primary` |

业务示例：

| 业务值 | 类型 |
| --- | --- |
| `AVAILABLE` | `success` |
| `COMPLETED` | `success` |
| `RUNNING` | `warning` |
| `FAILED` | `danger` |
| `PENDING` | `info` |
| `ACTIVE` | `success` |
| `DISABLED` | `danger` |
| `Admin` | `danger` |
| `User` | `primary` |
| `OPEN` alert | `danger` |
| `RESOLVED` alert | `success` |

## 登录页规范

登录页可以比后台页更品牌化，但仍保持克制。

布局：

- 左右双栏，各占一半。
- 左侧为品牌区。
- 右侧为登录表单区。
- 页面高度至少 `100vh`。

左侧品牌区：

- 深色渐变背景：`linear-gradient(135deg, #1e1e2d 0%, #151521 100%)`
- padding：`60px`
- 顶部品牌 logo + 名称
- 底部附近放口号标题和说明
- 可使用一个低透明度径向光斑作为唯一装饰

右侧表单区：

- 背景白色
- 表单容器最大宽度：`400px`
- 表单容器 padding：`40px`
- 标题：`32px`、`700`
- 说明文字：`15px`、muted
- 登录按钮满宽，高度 `48px`

## 图标规范

- 优先使用 `@element-plus/icons-vue`。
- 侧边栏每个一级菜单必须有图标。
- Dashboard 指标卡使用图标块表达类别。
- 按钮图标只用于明确动作：新增、上传、下载、刷新、用户、时间、告警等。
- 不手写自定义 SVG 图标，除非产品品牌 logo 必须定制。

## 动效规范

动效保持轻量，服务于状态反馈。

页面切换：

```css
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateY(15px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateY(-15px);
}
```

其他规则：

- 卡片 hover 只增强阴影。
- 用户菜单 hover 只改变背景。
- 输入 focus 只改变描边。
- 不使用复杂页面动画、粒子动画、大面积动态渐变。

## 国际化与文案

文案风格应短、具体、面向操作。

规则：

- 页面标题使用名词：仪表盘、数据库实例、备份管理、审计日志。
- 主按钮使用动词或动宾结构：新增、运行备份、下载、确认。
- 状态值可以保留后端枚举，但用户侧可通过 i18n 转译。
- 表单 placeholder 说明输入目标，不写长段教程。
- 错误和确认提示使用 Element Plus Message / MessageBox。

## 响应式建议

当前 DBVault 更偏桌面后台。复刻时建议优先保证桌面体验，再补移动端。

桌面优先规则：

- 默认设计宽度面向 `1280px+`。
- 侧边栏固定 `260px`。
- 表格优先横向信息完整。
- 操作列固定右侧。

移动端增强建议：

- 小屏下侧边栏改为抽屉或折叠菜单。
- Header 保留标题和用户菜单，隐藏次要信息。
- 表格页可切换为卡片列表，但状态标签、操作优先级保持一致。
- 筛选区允许换行，gap 保持 `10px`。

## 可复刻组件清单

在新项目中建议先封装这些组件：

- `AppLayout`：侧边栏 + header + 内容区
- `SidebarMenu`：权限过滤后的图标菜单
- `PageCard`：统一卡片容器
- `PageToolbar`：标题 + 筛选 + 操作区
- `DataTable`：表格默认样式和分页
- `StatusTag`：业务状态到 Element Plus tag type 的映射
- `FormDialog`：创建/编辑弹窗模板
- `StatCard`：Dashboard 指标卡
- `ChartCard`：图表卡片

## 快速复刻步骤

1. 安装 Vue 3、Vite、Element Plus、Element Plus Icons、ECharts。
2. 创建全局 `style.css`，复制色彩 token 和 Element Plus 覆盖变量。
3. 实现 `AppLayout`：`260px` 深色侧边栏、`70px` 顶栏、`30px` 内容 padding。
4. 配置路由 meta title，由 Header 自动读取显示。
5. 所有业务资源页使用“主卡片 + 工具栏 + 表格 + 分页 + 弹窗表单”。
6. Dashboard 使用“统计卡 + 图表卡 + 最近数据表”。
7. 建立统一 `StatusTag` 映射，禁止每个页面随意定义状态颜色。
8. 建立统一日期、文件大小、枚举显示格式化工具。
9. 保持主色克制，避免新增无业务含义的装饰色。
10. 最后补登录页左右分栏品牌模板。

## 复刻公式

**Element Plus 企业后台骨架 + Slate/Blue token + 卡片化数据容器 + 高密度表格 + 语义状态标签 + 对话框表单流。**

只要保持这六项一致，即使业务领域从数据库备份换成监控、权限、工单、资产或部署平台，也能快速得到 DBVault 同款前端气质。
