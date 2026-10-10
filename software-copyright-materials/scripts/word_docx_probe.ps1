# 调查数据拟废卷信息处理平台 V1.0
# 软著材料 skill 后端探针：用 Word COM 读 DOCX 的真实分页与字数。
#
# 为什么需要它：OfficeCLI 的 `view stats --page-count` 只给总页数，
# 「40 页全绿但第 40 页只有 16 行」这种缺陷它看不见；中文「字数」也只有 Word
# 自己能给（标点计入，与自算的汉字数差 10% 左右）。
#
# 用法：
#   pwsh word_docx_probe.ps1 -Path manual.docx -Mode stats
#   pwsh word_docx_probe.ps1 -Path code.docx -Mode layout -ExpectedPages 40 -MinLinesPerPage 50
#
# 约定：
#   * 只在**副本**上操作，交付文件不打开、不写入（Word 会改字段缓存与时间戳）；
#   * 结束时只清理本次新建的隐藏 WINWORD 实例（baseline pid 差集），不碰用户可见的 Word；
#   * 任何失败都返回 success=false，由调用方决定是记警告还是判失败。
param(
  [Parameter(Mandatory = $true)][string]$Path,
  [ValidateSet('stats', 'layout')][string]$Mode = 'stats',
  [int]$ExpectedPages = 0,
  [int]$MinLinesPerPage = 0,
  [string]$WorkDir = ''
)

$ErrorActionPreference = 'Stop'
$baselineWord = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
$result = [ordered]@{
  success         = $false
  file            = ''
  mode            = $Mode
  pages           = $null
  paragraphs      = $null
  words           = $null
  characters      = $null
  minPageLines    = $null
  lastPageLines   = $null
  maxPageLines    = $null
  perPage         = @()
  expectedPages   = $ExpectedPages
  minLinesPerPage = $MinLinesPerPage
  error           = ''
}

$word = $null
$doc = $null
$copy = $null
try {
  $resolved = (Resolve-Path -LiteralPath $Path).Path
  $result.file = [System.IO.Path]::GetFileName($resolved)
  if (-not $WorkDir) { $WorkDir = Join-Path ([System.IO.Path]::GetTempPath()) 'dsh-word-probe' }
  New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
  $copy = Join-Path $WorkDir ([System.IO.Path]::GetFileNameWithoutExtension($resolved) + '-' + [System.Guid]::NewGuid().ToString('N').Substring(0, 8) + [System.IO.Path]::GetExtension($resolved))
  Copy-Item -LiteralPath $resolved -Destination $copy -Force

  $word = New-Object -ComObject Word.Application
  $word.Visible = $false
  $word.DisplayAlerts = 0
  $doc = $word.Documents.Open($copy, $false, $true)
  $doc.Repaginate()
  $result.pages = [int]$doc.ComputeStatistics(2)
  $result.paragraphs = [int]$doc.Paragraphs.Count
  $result.words = [int]$doc.ComputeStatistics(0)
  $result.characters = [int]$doc.ComputeStatistics(3)

  if ($Mode -eq 'layout') {
    $counts = @{}
    for ($i = 1; $i -le $result.paragraphs; $i++) {
      $page = [int]$doc.Paragraphs.Item($i).Range.Information(3)
      if ($counts.ContainsKey($page)) { $counts[$page] = [int]$counts[$page] + 1 } else { $counts[$page] = 1 }
    }
    $perPage = @()
    for ($page = 1; $page -le $result.pages; $page++) {
      $value = 0
      if ($counts.ContainsKey($page)) { $value = [int]$counts[$page] }
      $perPage += $value
    }
    $result.perPage = $perPage
    if ($perPage.Count -gt 0) {
      $result.minPageLines = ($perPage | Measure-Object -Minimum).Minimum
      $result.maxPageLines = ($perPage | Measure-Object -Maximum).Maximum
      $result.lastPageLines = $perPage[$perPage.Count - 1]
    }
  }
  $result.success = $true
}
catch {
  $result.error = $_.Exception.Message
}
finally {
  if ($doc) { try { $doc.Close(0) } catch { } }
  if ($word) {
    try { $word.Quit() } catch { }
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
  }
  [GC]::Collect()
  if ($copy -and (Test-Path -LiteralPath $copy)) { Remove-Item -LiteralPath $copy -Force -ErrorAction SilentlyContinue }
  Get-Process WINWORD -ErrorAction SilentlyContinue |
    Where-Object { [string]::IsNullOrEmpty($_.MainWindowTitle) -and ($baselineWord -notcontains $_.Id) } |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
}

$result | ConvertTo-Json -Depth 4 -Compress
if (-not $result.success) { exit 1 }
