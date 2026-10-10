# 调查数据拟废卷信息处理平台 V1.0
# 软著材料 skill：把官方申请表模板填成一份可提交的文件。
#
# 为什么需要它：skill 原来只产出 申请表信息.txt，而登记时真正要提交的是官方
# 模板那份 .doc/.docx。手工誊抄既慢又容易漏字段，还会出现「申请表信息.txt 里
# 是长版主要功能、纸质表里还是短版」这种不一致。
#
# 设计约束：
#   * 数据源只有 草稿/申请表信息.md —— 不另立一套口径；
#   * 默认 dry-run：先打印「标签 → 目标单元格 / 原值 / 新值」，加 -Apply 才写；
#   * 锚点（标签）不全就整体不写，绝不半途改一半；
#   * 模板原件不动，另存为 <软件全称>-著作权申请表(已填写).docx；
#   * 缺值（证件类型/号码、联系人信息）不猜，写完后逐格回读并把空位列出来。
#
# 用法：
#   pwsh fill_application_form.ps1 -Template "<官方模板.doc>"                 # 预演
#   pwsh fill_application_form.ps1 -Template "<官方模板.doc>" -Apply          # 写入
#   pwsh fill_application_form.ps1 -Verify "<已填写.docx>"                    # 只回读校验
param(
  [string]$Template = '',
  [string]$Draft = '软件著作权申请资料/草稿/申请表信息.md',
  [string]$Out = '',
  [string]$WorkCopy = '',
  [switch]$Apply,
  [string]$Verify = ''
)

$ErrorActionPreference = 'Stop'

# 著作权人区块：表头在第 11 行，取值填在它下面一行的同列
$OWNER_ROW = 12
$OWNER_NAME_COL = 2

function Get-CellText($cell) { ($cell.Range.Text -replace "[`r`n`a`v`t]", ' ').Trim() }

function Get-CellMap($table) {
  $map = @{}
  $list = @()
  foreach ($cell in $table.Range.Cells) {
    $list += $cell
    $map["$($cell.RowIndex),$($cell.ColumnIndex)"] = $cell
  }
  return @{ List = $list; Map = $map }
}

function Read-DraftFields([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) { throw "找不到申请表草稿：$path" }
  $fields = @{}
  foreach ($line in (Get-Content -LiteralPath $path -Encoding UTF8)) {
    if ($line -match '^➤(?<name>[^：]+)：(?<value>.*)$') {
      $fields[$Matches['name'].Trim()] = $Matches['value'].Trim()
    }
  }
  if ($fields.Count -eq 0) { throw "未能从 $path 解析出任何 ➤ 字段" }
  return $fields
}

function Require-Field($fields, [string]$name) {
  $value = [string]$fields[$name]
  if ([string]::IsNullOrWhiteSpace($value) -or $value -like '*待用户确认*') {
    throw "草稿字段「$name」为空或仍是待确认值：'$value'"
  }
  return $value
}

function Get-Plan($fields, $table1, $table2) {
  $completeDate = Require-Field $fields '开发完成日期'
  if ($completeDate -match '^(\d{4})-(\d{2})-(\d{2})$') {
    $completeDate = "{0} 年 {1} 月 {2} 日" -f $Matches[1], [int]$Matches[2], [int]$Matches[3]
  }
  $labelFills = [ordered]@{
    '软件名称'             = Require-Field $fields '软件全称'
    '版本号'               = Require-Field $fields '版本号'
    '软件简称'             = Require-Field $fields '软件简称'
    '软件分类'             = Require-Field $fields '软件分类'
    '开发完成日期'         = $completeDate
    '开发的硬件环境'       = Require-Field $fields '开发的硬件环境'
    '运行的硬件环境'       = Require-Field $fields '运行的硬件环境'
    '开发该软件的操作系统' = Require-Field $fields '开发该软件的操作系统'
    '软件开发环境'         = Require-Field $fields '软件开发环境 / 开发工具'
    '该软件的运行平台'     = Require-Field $fields '该软件的运行平台 / 操作系统'
    '软件运行支撑环境'     = Require-Field $fields '软件运行支撑环境 / 支持软件'
    '编程语言'             = Require-Field $fields '编程语言'
    '源程序量'             = Require-Field $fields '源程序量'
    '开发目的'             = Require-Field $fields '开发目的'
    '面向领域'             = Require-Field $fields '面向领域 / 行业'
    '主要功能'             = Require-Field $fields '软件的主要功能'
    '技术特点'             = Require-Field $fields '软件的技术特点'
  }
  $plan = @()
  for ($i = 0; $i -lt $table1.List.Count; $i++) {
    $text = Get-CellText $table1.List[$i]
    foreach ($label in $labelFills.Keys) {
      if ($text.StartsWith($label)) {
        if ($i + 1 -ge $table1.List.Count) { throw "标签「$label」没有右侧单元格" }
        $value = [string]$labelFills[$label]
        if ($label -eq '软件分类') {
          # 该单元格里是模板的「注：1.应用软件 …」选项说明：保留说明，取值写在前面一行。
          # 只在单元格确实还是模板说明时才拼接，重复运行不会把取值叠加两遍。
          $noteText = Get-CellText $table1.List[$i + 1]
          if ($noteText -and $noteText.StartsWith('注：')) { $value = $value + "`n" + $noteText }
        }
        $plan += [pscustomobject]@{
          Label = $label; Cell = $table1.List[$i + 1]; Row = $table1.List[$i + 1].RowIndex
          Col = $table1.List[$i + 1].ColumnIndex; Value = $value
        }
        break
      }
    }
  }
  $owner = Require-Field $fields '著作权人'
  foreach ($entry in @(
      @{ Key = "$OWNER_ROW,$OWNER_NAME_COL"; Value = $owner },
      @{ Key = "$OWNER_ROW,3"; Value = '法人' },
      @{ Key = "$OWNER_ROW,6"; Value = '中国' })) {
    if (-not $table1.Map.ContainsKey($entry.Key)) { throw "著作权人区块缺少单元格 $($entry.Key)" }
    $cell = $table1.Map[$entry.Key]
    $plan += [pscustomobject]@{
      Label = "著作权人[$($entry.Key)]"; Cell = $cell; Row = $cell.RowIndex
      Col = $cell.ColumnIndex; Value = [string]$entry.Value
    }
  }
  for ($i = 0; $i -lt $table2.List.Count; $i++) {
    if ((Get-CellText $table2.List[$i]) -eq '姓名或名称') {
      $plan += [pscustomobject]@{
        Label = '申请人姓名或名称'; Cell = $table2.List[$i + 1]; Row = $table2.List[$i + 1].RowIndex
        Col = $table2.List[$i + 1].ColumnIndex; Value = $owner
      }
      break
    }
  }
  return $plan
}

function Show-Plan($plan) {
  foreach ($item in $plan) {
    $old = Get-CellText $item.Cell
    if ($old.Length -gt 34) { $old = $old.Substring(0, 34) + '…' }
    $new = $item.Value
    if ($new.Length -gt 34) { $new = $new.Substring(0, 34) + '…' }
    "{0,-22} R{1}C{2}  原值[{3}]  新值[{4}]" -f $item.Label, $item.Row, $item.Col, $old, $new
  }
}

function Show-BlankCells($table1, $table2) {
  '--- 仍为空的填写位（需要用户提供，脚本不猜）---'
  for ($t = 1; $t -le 2; $t++) {
    $table = if ($t -eq 1) { $table1 } else { $table2 }
    foreach ($key in ($table.Map.Keys | Sort-Object { [int]($_ -split ',')[0] }, { [int]($_ -split ',')[1] })) {
      $cell = $table.Map[$key]
      if ((Get-CellText $cell)) { continue }
      $row = $cell.RowIndex; $col = $cell.ColumnIndex
      $label = ''
      foreach ($offset in 1..3) {
        foreach ($candidateKey in @("$row,$($col - $offset)", "$($row - $offset),$col")) {
          if ($table.Map.ContainsKey($candidateKey)) {
            $candidate = Get-CellText $table.Map[$candidateKey]
            if ($candidate) { $label = $candidate; break }
          }
        }
        if ($label) { break }
      }
      if ($label.Length -gt 30) { $label = $label.Substring(0, 30) + '…' }
      "表{0} R{1}C{2} 空：{3}" -f $t, $row, $col, $label
    }
  }
}

if ($Verify) {
  if (-not (Test-Path -LiteralPath $Verify)) { throw "找不到要校验的文件：$Verify" }
  $ResolveVerify = (Resolve-Path -LiteralPath $Verify).Path
} elseif (-not $Template) {
  throw "需要 -Template <官方模板>（写入模式）或 -Verify <已填写文件>（校验模式）"
}

$baselineWord = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
$word = $null
$doc = $null
try {
  $word = New-Object -ComObject Word.Application
  $word.Visible = $false
  $word.DisplayAlerts = 0

  if ($Verify) {
    $doc = $word.Documents.Open($ResolveVerify, $false, $true)
    $table1 = Get-CellMap $doc.Tables.Item(1)
    $table2 = Get-CellMap $doc.Tables.Item(2)
    $fields = if (Test-Path -LiteralPath $Draft) { Read-DraftFields $Draft } else { @{} }
    $failed = @()
    if ($fields.Count -gt 0) {
      # 用与写入完全相同的映射算出「草稿要求的值」，再逐格比对 —— 手工誊抄最容易在这里露馅
      $expected = Get-Plan $fields $table1 $table2
      foreach ($item in $expected) {
        $actual = Get-CellText $item.Cell
        $want = $item.Value
        $normalizedActual = ($actual -replace '\s+', '')
        $normalizedWant = ($want -replace '\s+', '')
        if ($normalizedActual -eq $normalizedWant) {
          "OK   {0} = {1}" -f $item.Label, ($actual.Substring(0, [Math]::Min(26, $actual.Length)))
        } elseif ($normalizedActual -like "$normalizedWant*") {
          "OK   {0} = {1}（含模板说明）" -f $item.Label, ($actual.Substring(0, [Math]::Min(20, $actual.Length)))
        } else {
          $shownActual = if ($actual.Length -gt 30) { $actual.Substring(0, 30) + '…' } else { $actual }
          $shownWant = if ($want.Length -gt 30) { $want.Substring(0, 30) + '…' } else { $want }
          $failed += "$($item.Label)：表单[$shownActual] 与草稿[$shownWant] 不一致"
        }
      }
    } else {
      '未提供草稿，跳过逐格比对，只列空位。'
    }
    Show-BlankCells $table1 $table2
    if ($failed.Count) { $failed | ForEach-Object { "FAIL $_" }; exit 1 }
    'RESULT: PASS'
    exit 0
  }

  $fields = Read-DraftFields $Draft
  if (-not $WorkCopy) {
    # 工作副本保留模板扩展名（.doc / .docx 都能被 Word 打开，扩展名错了会让 Word 报警告）
    $extension = [System.IO.Path]::GetExtension((Resolve-Path -LiteralPath $Template).Path)
    if (-not $extension) { $extension = '.doc' }
    $WorkCopy = Join-Path ([System.IO.Path]::GetTempPath()) ('dsh-application-form-' + [System.Guid]::NewGuid().ToString('N').Substring(0, 8) + $extension)
  }
  Copy-Item -LiteralPath $Template -Destination $WorkCopy -Force
  $doc = $word.Documents.Open($WorkCopy, $false, $false)
  $table1 = Get-CellMap $doc.Tables.Item(1)
  $table2 = Get-CellMap $doc.Tables.Item(2)
  $plan = Get-Plan $fields $table1 $table2

  $noteCell = $table1.Map['3,3']
  if ($noteCell) { "软件作品说明当前值（模板常把 ⊙ 打在「修改」上）：$(Get-CellText $noteCell)" }
  Show-Plan $plan
  "计划填写 {0} 个单元格" -f $plan.Count

  if (-not $Apply) {
    'DRY_RUN：未写入任何内容；确认无误后加 -Apply'
    exit 0
  }

  foreach ($item in $plan) { $item.Cell.Range.Text = $item.Value }
  if ($noteCell) {
    foreach ($pair in @(@('○ 原创', '⊙ 原创'), @('⊙ 修改', '○ 修改'))) {
      $find = $doc.Content.Find
      $find.ClearFormatting()
      $find.Replacement.ClearFormatting()
      $ok = $find.Execute($pair[0], $false, $false, $false, $false, $false, $true, 1, $false, $pair[1], 2)
      "标记替换 {0} -> {1} : {2}" -f $pair[0], $pair[1], $ok
    }
  }
  if (-not $Out) {
    $softwareName = Require-Field $fields '软件全称'
    $templateDir = Split-Path -Parent (Resolve-Path -LiteralPath $Template).Path
    $Out = Join-Path $templateDir ("$softwareName-著作权申请表(已填写).docx")
  }
  $doc.SaveAs2($Out, 16)
  "已保存：$Out"
  Show-BlankCells $table1 $table2
}
finally {
  if ($doc) { try { $doc.Close(0) } catch { } }
  if ($word) {
    try { $word.Quit() } catch { }
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
  }
  [GC]::Collect()
  Get-Process WINWORD -ErrorAction SilentlyContinue |
    Where-Object { [string]::IsNullOrEmpty($_.MainWindowTitle) -and ($baselineWord -notcontains $_.Id) } |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
  if ($WorkCopy -and (Test-Path -LiteralPath $WorkCopy) -and $WorkCopy -ne $Template) {
    Remove-Item -LiteralPath $WorkCopy -Force -ErrorAction SilentlyContinue
  }
}
