$ErrorActionPreference = 'Stop'
$alreadyRunning = @(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app = $null
$deck = $null
try {
    $app = New-Object -ComObject PowerPoint.Application
    $reports = @()
    $inputs = @(@{file='TRIAGE_workflow_editable.pptx'; image='powerpoint-figure-1.png'; height=1200}, @{file='Surufatinib_results_editable.pptx'; image='powerpoint-figure-2.png'; height=1360})
    foreach ($item in $inputs) {
        $deck = $app.Presentations.Open((Join-Path $PSScriptRoot $item.file), -1, 0, 0)
        $slide = $deck.Slides.Item(1)
        $slide.Export((Join-Path $PSScriptRoot $item.image), 'PNG', 1800, $item.height)
        if ($item.file -eq 'TRIAGE_workflow_editable.pptx') { $deck.SaveAs((Join-Path $PSScriptRoot 'workflow-native.pdf'), 32) }
        $issues = @()
        $texts = 0
        for ($i=1; $i -le $slide.Shapes.Count; $i++) {
            $shape = $slide.Shapes.Item($i)
            if ($shape.HasTextFrame -and $shape.TextFrame.HasText) {
                $texts++
                $range = $shape.TextFrame2.TextRange
                if ($range.BoundWidth -gt $shape.Width + 1.5 -or $range.BoundHeight -gt $shape.Height + 1.5) {
                    $issues += [pscustomobject]@{name=$shape.Name; text=$range.Text; width=$shape.Width; height=$shape.Height; textWidth=$range.BoundWidth; textHeight=$range.BoundHeight}
                }
            }
        }
        $reports += [pscustomobject]@{file=$item.file; opened=$true; slides=$deck.Slides.Count; shapes=$slide.Shapes.Count; textBoxes=$texts; textOverflow=$issues}
        $deck.Close()
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($deck)
        $deck = $null
    }
    $report = [pscustomobject]@{decks=$reports; passed=(@($reports | Where-Object { $_.textOverflow.Count -gt 0 }).Count -eq 0)}
    $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'powerpoint-validation.json') -Encoding utf8
    $report | ConvertTo-Json -Depth 6
}
finally {
    if ($null -ne $deck) { $deck.Close() }
    if ($null -ne $app -and -not $alreadyRunning) { $app.Quit() }
    if ($null -ne $deck) { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($deck) }
    if ($null -ne $app) { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($app) }
}
