$port = 8000
$root = "C:\Users\arenn\Documents\Codex\2026-06-30\opencall-token\outputs\opencall-token"

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$port/")
$listener.Start()

Write-Host ""
Write-Host "  OpenCall Token 本地测试服务器"
Write-Host "  http://localhost:$port"
Write-Host "  按 Ctrl+C 停止"
Write-Host ""

while ($listener.IsListening) {
  $ctx = $listener.GetContext()
  $path = $ctx.Request.Url.AbsolutePath.TrimStart('/')
  if (!$path) { $path = "index.html" }
  $file = Join-Path $root $path

  if (Test-Path $file) {
    $bytes = [System.IO.File]::ReadAllBytes($file)

    # 设置正确的 MIME 类型
    $ext = [System.IO.Path]::GetExtension($file)
    switch ($ext) {
      ".html" { $ctx.Response.ContentType = "text/html; charset=utf-8" }
      ".js"   { $ctx.Response.ContentType = "application/javascript; charset=utf-8" }
      ".css"  { $ctx.Response.ContentType = "text/css; charset=utf-8" }
      default { $ctx.Response.ContentType = "text/plain" }
    }

    $ctx.Response.ContentLength64 = $bytes.Length
    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    Write-Host "  [200] $path"
  } else {
    $ctx.Response.StatusCode = 404
    Write-Host "  [404] $path"
  }

  $ctx.Response.Close()
}