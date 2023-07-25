# Usage:
# flatten.ps1 <path> <filter>
$targetDir = Convert-Path $args[0]
Get-ChildItem -LiteralPath $targetDir -Directory |
Get-ChildItem -Recurse -File -Filter $args[1] |
Move-Item -Destination {
  Join-Path $targetDir ` $_
} -Whatif:$False