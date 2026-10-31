param([string]$EnvPath = (Join-Path $PSScriptRoot '..\.env'))
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$EnvPath = [IO.Path]::GetFullPath($EnvPath)
if (-not (Test-Path -LiteralPath $EnvPath -PathType Leaf)) {
    throw 'Run scripts/setup_a.py first to create the local .env file.'
}
$form = New-Object Windows.Forms.Form
$form.Text = 'Lab 9 - Local OpenAI key'
$form.ClientSize = New-Object Drawing.Size(590,220)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.TopMost = $true
$label = New-Object Windows.Forms.Label
$label.SetBounds(20,20,550,45)
$label.Text = 'Paste your OpenAI API key below. It stays in the local .env file. Do not send it in chat or commit it to Git.'
$inputBox = New-Object Windows.Forms.TextBox
$inputBox.SetBounds(20,75,550,28)
$inputBox.UseSystemPasswordChar = $true
$inputBox.MaxLength = 512
$status = New-Object Windows.Forms.Label
$status.SetBounds(20,115,550,35)
$status.Text = 'Used only for embedding requests to the OpenAI API.'
$link = New-Object Windows.Forms.LinkLabel
$link.SetBounds(20,170,240,25)
$link.Text = 'Open official API key page'
$link.Add_LinkClicked({ Start-Process 'https://platform.openai.com/api-keys' })
$save = New-Object Windows.Forms.Button
$save.SetBounds(440,165,130,32)
$save.Text = 'Save locally'
$save.Add_Click({
    $keyValue = $inputBox.Text.Trim()
    if (-not $keyValue.StartsWith('sk-') -or $keyValue.Length -lt 20 -or $keyValue -match '\s') {
        $status.Text = 'Please paste a complete API key (starts with sk-).'
        return
    }
    try {
        $lines = [IO.File]::ReadAllLines($EnvPath)
        $kept = @($lines | Where-Object { $_ -notmatch '^\s*OPENAI_API_KEY\s*=' })
        [IO.File]::WriteAllLines($EnvPath, @($kept + ('OPENAI_API_KEY=' + $keyValue)), (New-Object Text.UTF8Encoding($false)))
        $inputBox.Clear()
        $keyValue = $null
        $form.DialogResult = [Windows.Forms.DialogResult]::OK
        $form.Close()
    } catch {
        $status.Text = 'Could not save the file. Check local file permissions.'
    }
})
$form.Controls.AddRange(@($label,$inputBox,$status,$link,$save))
$form.AcceptButton = $save
$null = $form.ShowDialog()
$inputBox.Clear()
$form.Dispose()
