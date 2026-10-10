# 调查数据拟废卷信息处理平台 V1.0
# 软著材料 skill：只读导出官方申请表模板的字段结构，用来建立「字段口径来源」。
#
# 为什么需要它：官方模板里的注（例如「主要功能（注：汉字字符加标点500字到1300个以内）」、
# 「技术特点（注：汉字字符加标点100个以内，所列15个选择跟软件相关的，不在100个字符）」）
# 往往就是口径变更的**唯一权威来源**，却只躺在 .doc 里。把它们抄成
# 草稿/字段口径来源.md 之后，口径判定、门禁常量与说明文档才有据可查。
#
# 用法：
#   pwsh dump_form_template.ps1 -Path "<官方模板.doc>" -Out "软件著作权申请资料/草稿/字段口径来源.md"
#   pwsh dump_form_template.ps1 -Path "<官方模板.doc>"            # 只打印到 stdout
param(
  [Parameter(Mandatory = $true)][string]$Path,
  [string]$Out = '',
  [int]$MaxCellChars = 200
)

$ErrorActionPreference = 'Stop'
$baselineWord = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
$word = $null
$doc = $null
$lines = New-Object System.Collections.Generic.List[string]
try {
  $resolved = (Resolve-Path -LiteralPath $Path).Path
  $word = New-Object -ComObject Word.Application
  $word.Visible = $false
  $word.DisplayAlerts = 0
  $doc = $word.Documents.Open($resolved, $false, $true)

  $lines.Add("# 官方申请表字段口径来源")
  $lines.Add("")
  $lines.Add("来源文件：``$([System.IO.Path]::GetFileName($resolved))``（只读导出，模板本身未被修改）")
  $lines.Add("")
  $lines.Add("## 表格结构")
  $lines.Add("")
  for ($t = 1; $t -le $doc.Tables.Count; $t++) {
    $table = $doc.Tables.Item($t)
    $lines.Add("### 表格 $t（$($table.Rows.Count) 行 × $($table.Columns.Count) 列）")
    $lines.Add("")
    $lines.Add("| 单元格 | 文本 |")
    $lines.Add("| --- | --- |")
    foreach ($cell in $table.Range.Cells) {
      $text = ($cell.Range.Text -replace "[`r`n`a`v`t]", ' ').Trim()
      if ($text.Length -gt $MaxCellChars) { $text = $text.Substring(0, $MaxCellChars) + '…' }
      $text = $text -replace '\|', '\|'
      $lines.Add("| R$($cell.RowIndex)C$($cell.ColumnIndex) | $text |")
    }
    $lines.Add("")
  }

  $lines.Add("## 字段注记（逐条摘出，作为口径判定的依据）")
  $lines.Add("")
  # 注意：官方模板里有的注记没有右括号（例如「主要功能 （注：汉字字符加标点500字到1300个以内」），
  # 所以闭合括号设为可选，避免把最关键的那条漏掉。
  $notePattern = [regex]'[（(]注[:：][^）)]*[）)]?'
  $seen = @{}
  for ($t = 1; $t -le $doc.Tables.Count; $t++) {
    foreach ($cell in $doc.Tables.Item($t).Range.Cells) {
      $text = ($cell.Range.Text -replace "[`r`n`a`v`t]", ' ').Trim()
      foreach ($match in $notePattern.Matches($text)) {
        $note = $match.Value
        if ($seen.ContainsKey($note)) { continue }
        $seen[$note] = $true
        $lines.Add("- $note")
      }
    }
  }
  if ($seen.Count -eq 0) { $lines.Add("- （模板里没有找到「（注：…）」形式的字段注记）") }

  if ($Out) {
    $outPath = [System.IO.Path]::GetFullPath($Out)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outPath) | Out-Null
    Set-Content -LiteralPath $outPath -Value $lines -Encoding utf8
    "已写出：$outPath"
    "字段注记 $($seen.Count) 条；表格 $($doc.Tables.Count) 张"
  } else {
    $lines
  }
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
}
