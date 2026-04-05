function Is-Placeholder {
    param([string]$value)
    if ($null -eq $value) { return $true }
    $v = $value.Trim()
    if ($v -eq '') { return $true }
    $norm = $v -replace '\s+', ''
    return $norm -match '^(--?|—|–|â€”|â€“)$'
}

function Normalize-Text {
    param([string]$value)
    if ($null -eq $value) { return '' }
    $v = $value.Trim()
    $v = $v -replace '`', ''
    $v = $v -replace '→', '->'
    $v = $v -replace '[\u2018\u2019]', "'"
    $v = $v -replace '[\u201C\u201D]', '"'
    $v = $v -replace '[\u2013\u2014]', '-'
    return $v
}

$mdPath = 'docs/DATA_DICTIONARY.md'
$lines = Get-Content -Path $mdPath
$rows = @()
$currentTable = ''
$inFieldTable = $false

foreach ($line in $lines) {
    if ($line -match '^###\s+\d+\.\d+\s+`([^`]+)`') {
        $currentTable = $matches[1]
        $inFieldTable = $false
        continue
    }

    if (-not $currentTable) { continue }

    if ($line -match '^\|\s*Field\s*\|\s*Data Type\s*\|\s*Size\s*\|') {
        $inFieldTable = $true
        continue
    }

    if (-not $inFieldTable) { continue }
    if ($line -match '^\|\s*-') { continue }

    if ($line -notmatch '^\|') {
        $inFieldTable = $false
        continue
    }

    $parts = $line -split '\|'
    if ($parts.Count -lt 8) { continue }

    $field = Normalize-Text $parts[1]
    if ([string]::IsNullOrWhiteSpace($field) -or $field -eq 'Field') { continue }

    $datatype = Normalize-Text $parts[2]
    $size = Normalize-Text $parts[3]
    $nullable = Normalize-Text $parts[4]
    $default = Normalize-Text $parts[5]
    $key = Normalize-Text $parts[6]
    $desc = Normalize-Text $parts[7]

    $type = $datatype
    if (-not (Is-Placeholder $size)) {
        if ($size -match '^\(.+\)$') {
            $type = "$datatype$size"
        } else {
            $type = "$datatype($size)"
        }
    }

    $constraints = @()
    if (-not (Is-Placeholder $key)) { $constraints += $key }
    if ($nullable -eq 'NO') { $constraints += 'NOT NULL' }
    elseif ($nullable -eq 'YES') { $constraints += 'NULLABLE' }
    if (-not (Is-Placeholder $default)) { $constraints += "DEFAULT $default" }

    $rows += [PSCustomObject]@{
        table = $currentTable
        field = $field
        type = $type
        constraints = ($constraints -join '; ')
        description = $desc
    }
}

$outCsvPath = 'docs/_data_dictionary_lines.csv'
$rows | ConvertTo-Csv -NoTypeInformation | Set-Content -Path $outCsvPath -Encoding UTF8

"Rows: $($rows.Count)"
$rows | Group-Object table | Sort-Object Name | ForEach-Object { "{0}: {1}" -f $_.Name, $_.Count }
"CSV written: $outCsvPath"
