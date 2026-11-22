#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$AuthUrl = 'http://127.0.0.1:8000',
    [string]$ProductUrl = 'http://127.0.0.1:8001',
    [string]$OrderUrl = 'http://127.0.0.1:8002',
    [string]$ReportUrl = 'http://127.0.0.1:8003',
    [string]$CredentialPath = '',
    [ValidateRange(1, 120)][int]$TimeoutSeconds = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http

if ([string]::IsNullOrWhiteSpace($CredentialPath)) {
    $CredentialPath = Join-Path $PSScriptRoot '../database/auth_demo_credentials.txt'
}

$AuthUrl = $AuthUrl.TrimEnd('/')
$ProductUrl = $ProductUrl.TrimEnd('/')
$OrderUrl = $OrderUrl.TrimEnd('/')
$ReportUrl = $ReportUrl.TrimEnd('/')

if (-not (Test-Path -LiteralPath $CredentialPath -PathType Leaf)) {
    throw 'Credential file not found. Initialize Auth demo data or supply -CredentialPath.'
}
$credential = Get-Content -LiteralPath $CredentialPath -Raw -Encoding UTF8 | ConvertFrom-Json

$handler = New-Object System.Net.Http.HttpClientHandler
$handler.AllowAutoRedirect = $false
$client = New-Object System.Net.Http.HttpClient($handler)
$client.Timeout = [TimeSpan]::FromSeconds($TimeoutSeconds)

$script:accessToken = $null
$checks = New-Object 'System.Collections.Generic.List[object]'
$createdSnapshots = New-Object 'System.Collections.Generic.List[long]'
$createdOrderCosts = New-Object 'System.Collections.Generic.List[long]'
$createdProductCosts = New-Object 'System.Collections.Generic.List[long]'
$createdOrders = New-Object 'System.Collections.Generic.List[long]'
$createdProducts = New-Object 'System.Collections.Generic.List[long]'
$cleanupErrors = New-Object 'System.Collections.Generic.List[string]'
$runId = [Guid]::NewGuid().ToString('N').Substring(0, 12)
$failure = $null

function Invoke-Api {
    param(
        [string]$BaseUrl,
        [string]$Method,
        [string]$Path,
        [object]$Body = $null,
        [switch]$Anonymous,
        [string]$Token = $script:accessToken
    )
    $request = New-Object System.Net.Http.HttpRequestMessage(
        (New-Object System.Net.Http.HttpMethod($Method)), "$BaseUrl$Path")
    $response = $null
    try {
        if (-not $Anonymous) {
            $request.Headers.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue('Bearer', $Token)
        }
        if ($null -ne $Body) {
            $jsonBody = ConvertTo-Json -InputObject $Body -Depth 12 -Compress
            $request.Content = New-Object System.Net.Http.StringContent($jsonBody, [Text.Encoding]::UTF8, 'application/json')
        }
        $response = $client.SendAsync($request).GetAwaiter().GetResult()
        $content = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        $payload = $null
        if (-not [string]::IsNullOrWhiteSpace($content)) {
            if ($content.TrimStart().StartsWith('[')) {
                $decoded = ConvertFrom-Json -InputObject $content
                if ($null -eq $decoded) { $payload = [object[]]@() }
                elseif ($decoded -is [Array]) { $payload = $decoded }
                else { $payload = [object[]]@($decoded) }
            }
            else { $payload = ConvertFrom-Json -InputObject $content }
        }
        $location = $null
        if ($null -ne $response.Headers.Location) { $location = $response.Headers.Location.ToString() }
        return [pscustomobject]@{
            Status = [int]$response.StatusCode
            Json = $payload
            Raw = $content
            Location = $location
        }
    }
    finally {
        if ($null -ne $response) { $response.Dispose() }
        $request.Dispose()
    }
}

function Assert-Status {
    param([object]$Response, [int]$Expected, [string]$Name)
    if ($Response.Status -ne $Expected) {
        throw "$Name expected HTTP $Expected, received HTTP $($Response.Status): $($Response.Raw)"
    }
    $checks.Add([pscustomobject]@{ name = $Name; status = $Response.Status; passed = $true })
    Write-Host "PASS $Name [$Expected]"
}

function Assert-Value {
    param([object]$Actual, [object]$Expected, [string]$Name)
    if ($Actual -cne $Expected) { throw "$Name expected '$Expected', got '$Actual'." }
    $checks.Add([pscustomobject]@{ name = $Name; passed = $true })
    Write-Host "PASS $Name"
}

function Login {
    $reply = Invoke-Api -BaseUrl $AuthUrl -Method POST -Path '/login/' -Anonymous -Body @{
        identifier = [string]$credential.identifier
        password = [string]$credential.password
    }
    if ($reply.Status -ne 200) { throw "Auth login failed with HTTP $($reply.Status)." }
    $script:accessToken = [string]$reply.Json.access
}

try {
    # 1. Public health + auth checks
    $reply = Invoke-Api -BaseUrl $ReportUrl -Method GET -Path '/health' -Anonymous
    Assert-Status $reply 200 'Report health endpoint'
    Assert-Value $reply.Json.status 'ok' 'Report health status'

    $reply = Invoke-Api -BaseUrl $ReportUrl -Method GET -Path '/reports/summary' -Anonymous
    Assert-Status $reply 401 'Report rejects anonymous request'

    Login
    Write-Host 'PASS Auth login [200]'

    # 2. Seed demo products via Product Service (port 8001)
    $reply = Invoke-Api -BaseUrl $ProductUrl -Method POST -Path '/products' -Body @{
        name = "ReportSmoke $runId A"; description = 'Smoke product A'; price = '100.00'; quantity = 40
    }
    Assert-Status $reply 201 'Create product A'
    $prodA = [long]$reply.Json.id
    $createdProducts.Add($prodA)

    $reply = Invoke-Api -BaseUrl $ProductUrl -Method POST -Path '/products' -Body @{
        name = "ReportSmoke $runId B"; description = 'Smoke product B'; price = '50.00'; quantity = 25
    }
    Assert-Status $reply 201 'Create product B'
    $prodB = [long]$reply.Json.id
    $createdProducts.Add($prodB)

    # 3. Configure unit costs in Report Service's independent DB (port 8003)
    $reply = Invoke-Api -BaseUrl $ReportUrl -Method POST -Path '/product_costs' -Body @{
        product_id = $prodA; unit_cost = '60.00'; note = 'Wholesale A'
    }
    Assert-Status $reply 201 'Create product cost A'
    $createdProductCosts.Add($prodA)
    Assert-Value $reply.Location "/product_costs/$prodA" 'Product cost Location header'

    $reply = Invoke-Api -BaseUrl $ReportUrl -Method POST -Path '/product_costs' -Body @{
        product_id = $prodB; unit_cost = '30.00'; note = 'Wholesale B'
    }
    Assert-Status $reply 201 'Create product cost B'
    $createdProductCosts.Add($prodB)

    # 4. Create orders via Order Service (port 8002)
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method POST -Path '/orders' -Body @{
        customer_name = "Smoke $runId Completed"; customer_email = 'smoke@example.com'
        items = @(@{ product_id = $prodA; quantity = 3 }, @{ product_id = $prodB; quantity = 2 })
    }
    Assert-Status $reply 201 'Create order 1'
    $orderCompleted = [long]$reply.Json.id
    $createdOrders.Add($orderCompleted)

    $reply = Invoke-Api -BaseUrl $OrderUrl -Method PUT -Path "/orders/$orderCompleted" -Body @{ status = 'completed' }
    Assert-Status $reply 200 'Complete order 1'

    $reply = Invoke-Api -BaseUrl $OrderUrl -Method POST -Path '/orders' -Body @{
        customer_name = "Smoke $runId Cancelled"; customer_email = 'smoke@example.com'
        items = @(@{ product_id = $prodA; quantity = 5 })
    }
    Assert-Status $reply 201 'Create order 2'
    $orderCancelled = [long]$reply.Json.id
    $createdOrders.Add($orderCancelled)

    $reply = Invoke-Api -BaseUrl $OrderUrl -Method PUT -Path "/orders/$orderCancelled" -Body @{ status = 'cancelled' }
    Assert-Status $reply 200 'Cancel order 2'

    # 5. Add extra shipping cost to completed order in Report Service
    $reply = Invoke-Api -BaseUrl $ReportUrl -Method POST -Path '/order_costs' -Body @{
        order_id = $orderCompleted; additional_cost = '15.00'; note = 'Delivery fee'
    }
    Assert-Status $reply 201 'Create order additional cost'
    $createdOrderCosts.Add($orderCompleted)

    # 6. Verify single-product reports
    # Product A: stock 40, sold 3, revenue 300.00, cost 180.00, profit 120.00
    $reply = Invoke-Api -BaseUrl $ReportUrl -Method GET -Path "/reports/products/$prodA"
    Assert-Status $reply 200 'GET /reports/products/{id} (A)'
    Assert-Value ([int]$reply.Json.product.stock_quantity) 40 'Product A stock quantity'
    Assert-Value ([int]$reply.Json.product.sold_quantity) 3 'Product A sold quantity'
    Assert-Value ([string]$reply.Json.product.revenue) '300.00' 'Product A revenue'
    Assert-Value ([string]$reply.Json.product.cost) '180.00' 'Product A cost'
    Assert-Value ([string]$reply.Json.product.profit) '120.00' 'Product A profit'

    # 7. Verify single-order report (completed)
    # Order 1: 3*100 + 2*50 = 400.00 rev; product cost = 3*60 + 2*30 = 240.00; extra = 15.00; total cost = 255.00; profit = 145.00
    $reply = Invoke-Api -BaseUrl $ReportUrl -Method GET -Path "/reports/orders/$orderCompleted"
    Assert-Status $reply 200 'GET /reports/orders/{id} (completed)'
    Assert-Value ([int]$reply.Json.order.sold_quantity) 5 'Completed order sold quantity'
    Assert-Value ([string]$reply.Json.order.revenue) '400.00' 'Completed order revenue'
    Assert-Value ([string]$reply.Json.order.product_cost) '240.00' 'Completed order product cost'
    Assert-Value ([string]$reply.Json.order.additional_cost) '15.00' 'Completed order additional cost'
    Assert-Value ([string]$reply.Json.order.total_cost) '255.00' 'Completed order total cost'
    Assert-Value ([string]$reply.Json.order.profit) '145.00' 'Completed order profit'

    # Cancelled order report -> 0 realized revenue/cost/profit
    $reply = Invoke-Api -BaseUrl $ReportUrl -Method GET -Path "/reports/orders/$orderCancelled"
    Assert-Status $reply 200 'GET /reports/orders/{id} (cancelled)'
    Assert-Value ([int]$reply.Json.order.sold_quantity) 0 'Cancelled order sold quantity'
    Assert-Value ([string]$reply.Json.order.revenue) '0.00' 'Cancelled order revenue'

    # 8. Verify live collection reports
    $reply = Invoke-Api -BaseUrl $ReportUrl -Method GET -Path '/reports/summary'
    Assert-Status $reply 200 'GET /reports/summary'
    $reply = Invoke-Api -BaseUrl $ReportUrl -Method GET -Path '/reports/products'
    Assert-Status $reply 200 'GET /reports/products'
    $reply = Invoke-Api -BaseUrl $ReportUrl -Method GET -Path '/reports/orders?status=completed'
    Assert-Status $reply 200 'GET /reports/orders?status=completed'

    # 9. Generate, read, and delete a persisted report snapshot in reports.sqlite3
    $reply = Invoke-Api -BaseUrl $ReportUrl -Method POST -Path '/reports' -Body @{
        title = "Smoke Snapshot $runId"; report_type = 'full'
    }
    Assert-Status $reply 201 'POST /reports (save snapshot)'
    $snapshotId = [long]$reply.Json.id
    $createdSnapshots.Add($snapshotId)
    Assert-Value $reply.Location "/reports/$snapshotId" 'Snapshot Location header'

    $reply = Invoke-Api -BaseUrl $ReportUrl -Method GET -Path "/reports/$snapshotId"
    Assert-Status $reply 200 'GET /reports/{id}'
    Assert-Value ([string]$reply.Json.title) "Smoke Snapshot $runId" 'Persisted snapshot title'

    $reply = Invoke-Api -BaseUrl $ReportUrl -Method DELETE -Path "/reports/$snapshotId"
    Assert-Status $reply 204 'DELETE /reports/{id}'
    [void]$createdSnapshots.Remove($snapshotId)
}
catch {
    $failure = $_.Exception.Message
}
finally {
    foreach ($id in $createdSnapshots) {
        try { [void](Invoke-Api -BaseUrl $ReportUrl -Method DELETE -Path "/reports/$id") }
        catch { $cleanupErrors.Add("Failed to clean snapshot $id") }
    }
    foreach ($id in $createdOrderCosts) {
        try { [void](Invoke-Api -BaseUrl $ReportUrl -Method DELETE -Path "/order_costs/$id") }
        catch { $cleanupErrors.Add("Failed to clean order_cost $id") }
    }
    foreach ($id in $createdProductCosts) {
        try { [void](Invoke-Api -BaseUrl $ReportUrl -Method DELETE -Path "/product_costs/$id") }
        catch { $cleanupErrors.Add("Failed to clean product_cost $id") }
    }
    foreach ($id in $createdOrders) {
        try { [void](Invoke-Api -BaseUrl $OrderUrl -Method DELETE -Path "/orders/$id") }
        catch { $cleanupErrors.Add("Failed to clean order $id") }
    }
    foreach ($id in $createdProducts) {
        try { [void](Invoke-Api -BaseUrl $ProductUrl -Method DELETE -Path "/products/$id") }
        catch { $cleanupErrors.Add("Failed to clean product $id") }
    }
    $client.Dispose()
    $handler.Dispose()
}

foreach ($err in $cleanupErrors) { Write-Warning $err }
if ($null -ne $failure) { throw "Report smoke test failed: $failure" }
if ($cleanupErrors.Count -gt 0) { throw 'Report smoke checks passed but cleanup had warnings.' }
Write-Host "Report smoke test passed: $($checks.Count) checks; all demo records cleaned up."
