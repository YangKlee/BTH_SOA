#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$AuthUrl = 'http://127.0.0.1:8000',
    [string]$ProductUrl = 'http://127.0.0.1:8001',
    [string]$OrderUrl = 'http://127.0.0.1:8002',
    [string]$CredentialPath = (Join-Path $PSScriptRoot '../database/auth_demo_credentials.txt'),
    [string]$EvidencePath,
    [ValidateRange(1, 120)][int]$TimeoutSeconds = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http

$AuthUrl = $AuthUrl.TrimEnd('/')
$ProductUrl = $ProductUrl.TrimEnd('/')
$OrderUrl = $OrderUrl.TrimEnd('/')
foreach ($baseUrl in @($AuthUrl, $ProductUrl, $OrderUrl)) {
    $parsed = $null
    if (-not [Uri]::TryCreate($baseUrl, [UriKind]::Absolute, [ref]$parsed) -or
        $parsed.Scheme -notin @('http', 'https') -or $parsed.UserInfo -or
        $parsed.Query -or $parsed.Fragment) {
        throw 'Service URLs must be absolute HTTP(S) URLs without credentials, query or fragment.'
    }
}
if (-not (Test-Path -LiteralPath $CredentialPath -PathType Leaf)) {
    throw 'Credential file not found. Initialize Auth demo data or supply -CredentialPath.'
}
$credential = Get-Content -LiteralPath $CredentialPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $credential.PSObject.Properties['identifier'] -or
    -not $credential.PSObject.Properties['password'] -or
    [string]::IsNullOrWhiteSpace([string]$credential.identifier) -or
    [string]::IsNullOrEmpty([string]$credential.password)) {
    throw 'Credential JSON must contain identifier and password.'
}

$handler = New-Object System.Net.Http.HttpClientHandler
$handler.AllowAutoRedirect = $false
$client = New-Object System.Net.Http.HttpClient($handler)
$client.Timeout = [TimeSpan]::FromSeconds($TimeoutSeconds)
$script:accessToken = $null
$checks = New-Object 'System.Collections.Generic.List[object]'
$createdOrders = New-Object 'System.Collections.Generic.List[long]'
$createdProducts = New-Object 'System.Collections.Generic.List[long]'
$cleanupErrors = New-Object 'System.Collections.Generic.List[string]'
$runId = [Guid]::NewGuid().ToString('N').Substring(0, 12)
$startedAt = [DateTimeOffset]::UtcNow.ToString('o')
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
        try {
            $response = $client.SendAsync($request).GetAwaiter().GetResult()
            $content = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        }
        catch {
            throw "Transport failure for $Method $Path. Check service URLs and running processes."
        }
        $payload = $null
        if (-not [string]::IsNullOrWhiteSpace($content)) {
            try {
                if ($content.TrimStart().StartsWith('[')) {
                    # Windows PowerShell 5.1 emits a JSON array as one array object.
                    # Wrapping the command in @() would introduce a nested array.
                    $decoded = ConvertFrom-Json -InputObject $content
                    if ($null -eq $decoded) { $payload = [object[]]@() }
                    elseif ($decoded -is [Array]) { $payload = $decoded }
                    else { $payload = [object[]]@($decoded) }
                }
                else { $payload = ConvertFrom-Json -InputObject $content }
            }
            catch { throw "Non-JSON response for $Method $Path (HTTP $([int]$response.StatusCode))." }
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
        throw "$Name expected HTTP $Expected, received HTTP $($Response.Status)."
    }
    if ($Expected -eq 204 -and -not [string]::IsNullOrEmpty($Response.Raw)) {
        throw "$Name expected an empty response body."
    }
    $checks.Add([pscustomobject]@{ name = $Name; status = $Response.Status; passed = $true })
    Write-Host "PASS $Name [$Expected]"
}

function Assert-Value {
    param([object]$Actual, [object]$Expected, [string]$Name)
    if ($Actual -cne $Expected) { throw "$Name did not match the expected value." }
    $checks.Add([pscustomobject]@{ name = $Name; passed = $true })
    Write-Host "PASS $Name"
}

function Login {
    $reply = Invoke-Api -BaseUrl $AuthUrl -Method POST -Path '/login/' -Anonymous -Body @{
        identifier = [string]$credential.identifier
        password = [string]$credential.password
    }
    if ($reply.Status -ne 200 -or -not $reply.Json.PSObject.Properties['access'] -or
        [string]::IsNullOrWhiteSpace([string]$reply.Json.access)) {
        throw 'Auth login failed. Check the local credential file.'
    }
    $script:accessToken = [string]$reply.Json.access
}

function Set-DemoProduct {
    param([long]$Id, [string]$Name, [string]$Price, [int]$Quantity)
    return Invoke-Api -BaseUrl $ProductUrl -Method PUT -Path "/products/$Id" -Body @{
        name = $Name; description = 'Order smoke test'; price = $Price; quantity = $Quantity
    }
}

try {
    Login
    $checks.Add([pscustomobject]@{ name = 'Auth login'; status = 200; passed = $true })
    Write-Host 'PASS Auth login [200]'
    $reply = Invoke-Api -BaseUrl $AuthUrl -Method GET -Path '/token/verify/'
    Assert-Status $reply 200 'Auth token verification'

    $reply = Invoke-Api -BaseUrl $OrderUrl -Method GET -Path '/orders' -Anonymous
    Assert-Status $reply 401 'Missing access token'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method GET -Path '/orders' -Token 'invalid-smoke-token'
    Assert-Status $reply 401 'Invalid access token'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method GET -Path '/orders/0'
    Assert-Status $reply 400 'Invalid order ID'

    $reply = Invoke-Api -BaseUrl $ProductUrl -Method POST -Path '/products' -Body @{
        name = "Smoke $runId pen"; description = 'Order smoke test'; price = '10.25'; quantity = 100
    }
    if ($reply.Status -eq 201) { $createdProducts.Add([long]$reply.Json.id) }
    Assert-Status $reply 201 'Create first demo product'
    $productOne = [long]$reply.Json.id
    $productOneName = [string]$reply.Json.name
    $reply = Invoke-Api -BaseUrl $ProductUrl -Method POST -Path '/products' -Body @{
        name = "Smoke $runId book"; description = 'Order smoke test'; price = '5.00'; quantity = 100
    }
    if ($reply.Status -eq 201) { $createdProducts.Add([long]$reply.Json.id) }
    Assert-Status $reply 201 'Create second demo product'
    $productTwo = [long]$reply.Json.id
    $productTwoName = [string]$reply.Json.name

    $reply = Invoke-Api -BaseUrl $OrderUrl -Method POST -Path '/orders' -Body @{
        customer_name = "Smoke $runId rejected"; customer_email = 'smoke@example.com'
        items = @(@{ product_id = $productOne; quantity = 1 }, @{ product_id = $productTwo; quantity = 101 })
    }
    if ($reply.Status -eq 201) { $createdOrders.Add([long]$reply.Json.id) }
    Assert-Status $reply 409 'Insufficient stock rejects nested order'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method GET -Path '/orders'
    Assert-Status $reply 200 'GET /orders after rejected create'
    $partialOrders = @($reply.Json | Where-Object { $_.customer_name -eq "Smoke $runId rejected" })
    foreach ($partial in $partialOrders) { $createdOrders.Add([long]$partial.id) }
    Assert-Value $partialOrders.Count 0 'Rejected order leaves no partial order'

    $reply = Invoke-Api -BaseUrl $OrderUrl -Method POST -Path '/orders' -Body @{
        customer_name = "Smoke $runId primary"; customer_email = 'smoke@example.com'
        items = @(@{ product_id = $productOne; quantity = 2 }, @{ product_id = $productTwo; quantity = 1 })
    }
    if ($reply.Status -eq 201) { $createdOrders.Add([long]$reply.Json.id) }
    Assert-Status $reply 201 'POST /orders'
    $primaryOrder = [long]$reply.Json.id
    Assert-Value $reply.Location "/orders/$primaryOrder" 'Order Location header'
    Assert-Value $reply.Json.status 'pending' 'New order defaults to pending'
    Assert-Value $reply.Json.total_amount '25.50' 'New order total'
    $itemOne = [long]@($reply.Json.items | Where-Object { $_.product_id -eq $productOne })[0].id
    $itemTwo = [long]@($reply.Json.items | Where-Object { $_.product_id -eq $productTwo })[0].id

    $reply = Invoke-Api -BaseUrl $OrderUrl -Method GET -Path '/orders'
    Assert-Status $reply 200 'GET /orders'
    Assert-Value (@($reply.Json | Where-Object { $_.id -eq $primaryOrder }).Count) 1 'Created order appears in collection'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method GET -Path "/orders/$primaryOrder"
    Assert-Status $reply 200 'GET /orders/{id}'
    Assert-Value @($reply.Json.items).Count 2 'Order detail embeds items'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method GET -Path '/order_items'
    Assert-Status $reply 200 'GET /order_items'
    Assert-Value (@($reply.Json | Where-Object { $_.order_id -eq $primaryOrder }).Count) 2 'Items collection includes both own items'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method GET -Path "/order_items/$itemOne"
    Assert-Status $reply 200 'GET /order_items/{id}'
    Assert-Value $reply.Json.unit_price '10.25' 'Initial item price snapshot'

    $reply = Invoke-Api -BaseUrl $OrderUrl -Method POST -Path '/order_items' -Body @{
        order_id = $primaryOrder; product_id = $productTwo; quantity = 1
    }
    Assert-Status $reply 409 'Duplicate product in order rejected'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method DELETE -Path "/order_items/$itemTwo"
    Assert-Status $reply 204 'DELETE /order_items/{id}'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method DELETE -Path "/order_items/$itemOne"
    Assert-Status $reply 409 'Last item cannot be deleted'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method POST -Path '/order_items' -Body @{
        order_id = $primaryOrder; product_id = $productTwo; quantity = 2
    }
    Assert-Status $reply 201 'POST /order_items'
    $itemTwo = [long]$reply.Json.id
    Assert-Value $reply.Location "/order_items/$itemTwo" 'Item Location header'

    $reply = Set-DemoProduct $productOne "Smoke $runId changed pen" '99.99' 100
    Assert-Status $reply 200 'Change current Product name and price'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method PUT -Path "/order_items/$itemOne" -Body @{ quantity = 3 }
    Assert-Status $reply 200 'PUT /order_items/{id}'
    Assert-Value $reply.Json.product_name $productOneName 'Item retains product name snapshot'
    Assert-Value $reply.Json.unit_price '10.25' 'Item retains original price after Product price changes'
    Assert-Value $reply.Json.total_price '30.75' 'Updated item total uses snapshot price'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method GET -Path "/orders/$primaryOrder"
    Assert-Status $reply 200 'Read order after item changes'
    Assert-Value $reply.Json.total_amount '40.75' 'Order total recalculated after item changes'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method PUT -Path "/order_items/$itemOne" -Body @{ quantity = 101 }
    Assert-Status $reply 409 'Item update cannot exceed stock'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method DELETE -Path "/order_items/$itemTwo"
    Assert-Status $reply 204 'Remove second item before completing order'

    $reply = Invoke-Api -BaseUrl $OrderUrl -Method POST -Path '/orders' -Body @{
        customer_name = "Smoke $runId cancellation"; customer_email = 'smoke@example.com'
        items = @(@{ product_id = $productTwo; quantity = 1 })
    }
    if ($reply.Status -eq 201) { $createdOrders.Add([long]$reply.Json.id) }
    Assert-Status $reply 201 'Create order for stock recheck and cancellation'
    $cancelOrder = [long]$reply.Json.id
    $reply = Set-DemoProduct $productTwo $productTwoName '5.00' 0
    Assert-Status $reply 200 'Reduce own demo product stock'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method PUT -Path "/orders/$cancelOrder" -Body @{ status = 'completed' }
    Assert-Status $reply 409 'Completion rechecks current stock'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method GET -Path "/orders/$cancelOrder"
    Assert-Status $reply 200 'Read order after failed completion'
    Assert-Value $reply.Json.status 'pending' 'Failed completion leaves order pending'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method PUT -Path "/orders/$cancelOrder" -Body @{ status = 'cancelled' }
    Assert-Status $reply 200 'Cancel pending order'
    Assert-Value $reply.Json.status 'cancelled' 'Cancelled state persisted'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method PUT -Path "/orders/$cancelOrder" -Body @{ status = 'completed' }
    Assert-Status $reply 409 'Cancelled order cannot become completed'
    $reply = Set-DemoProduct $productTwo $productTwoName '5.00' 100
    Assert-Status $reply 200 'Restore own demo product stock'

    $reply = Invoke-Api -BaseUrl $OrderUrl -Method PUT -Path "/orders/$primaryOrder" -Body @{ status = 'completed' }
    Assert-Status $reply 200 'PUT /orders/{id}'
    Assert-Value $reply.Json.status 'completed' 'Completed state persisted'
    Assert-Value $reply.Json.total_amount '30.75' 'Final total after item deletion'
    $completedAt = [string]$reply.Json.updated_at
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method PUT -Path "/orders/$primaryOrder" -Body @{ status = 'completed' }
    Assert-Status $reply 200 'Same status is idempotent'
    Assert-Value ([string]$reply.Json.updated_at) $completedAt 'Same status leaves updated_at unchanged'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method PUT -Path "/orders/$primaryOrder" -Body @{ status = 'cancelled' }
    Assert-Status $reply 409 'Completed order cannot become cancelled'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method PUT -Path "/order_items/$itemOne" -Body @{ quantity = 1 }
    Assert-Status $reply 409 'Completed order items cannot be updated'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method POST -Path '/order_items' -Body @{
        order_id = $primaryOrder; product_id = $productTwo; quantity = 1
    }
    Assert-Status $reply 409 'Completed order items cannot be added'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method DELETE -Path "/order_items/$itemOne"
    Assert-Status $reply 409 'Completed order items cannot be deleted'

    foreach ($productId in @($productOne, $productTwo)) {
        $reply = Invoke-Api -BaseUrl $ProductUrl -Method GET -Path "/products/$productId"
        Assert-Status $reply 200 "Read own demo Product $productId"
        Assert-Value ([int]$reply.Json.quantity) 100 "Product $productId stock unchanged by Order operations"
    }
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method DELETE -Path "/orders/$primaryOrder"
    Assert-Status $reply 204 'DELETE /orders/{id}'
    [void]$createdOrders.Remove($primaryOrder)
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method GET -Path "/order_items/$itemOne"
    Assert-Status $reply 404 'Order deletion cascades to items'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method DELETE -Path "/orders/$primaryOrder"
    Assert-Status $reply 404 'Deleting missing order returns 404'
    $reply = Invoke-Api -BaseUrl $OrderUrl -Method DELETE -Path "/orders/$cancelOrder"
    Assert-Status $reply 204 'Cancelled order can be deleted'
    [void]$createdOrders.Remove($cancelOrder)
}
catch {
    $failure = $_.Exception.Message
}
finally {
    # Cleanup targets only IDs returned by creates in this run; no global collection deletion.
    if ($createdOrders.Count -gt 0 -or $createdProducts.Count -gt 0) {
        try { Login }
        catch { $cleanupErrors.Add('Cleanup login failed; some own demo records may remain.') }
    }
    foreach ($orderId in $createdOrders) {
        try {
            $reply = Invoke-Api -BaseUrl $OrderUrl -Method DELETE -Path "/orders/$orderId"
            if ($reply.Status -notin @(204, 404)) { throw 'Unexpected cleanup response.' }
        }
        catch { $cleanupErrors.Add("Could not clean up own order ID $orderId.") }
    }
    foreach ($productId in $createdProducts) {
        try {
            $reply = Invoke-Api -BaseUrl $ProductUrl -Method DELETE -Path "/products/$productId"
            if ($reply.Status -notin @(204, 404)) { throw 'Unexpected cleanup response.' }
        }
        catch { $cleanupErrors.Add("Could not clean up own product ID $productId.") }
    }
    $client.Dispose()
    $handler.Dispose()
    $script:accessToken = $null
    $credential = $null
    $evidence = [ordered]@{
        run_id = $runId
        started_at_utc = $startedAt
        finished_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        passed = ($null -eq $failure -and $cleanupErrors.Count -eq 0)
        check_count = $checks.Count
        checks = @($checks.ToArray())
        failure = $failure
        cleanup_errors = @($cleanupErrors.ToArray())
    }
    if ($EvidencePath) {
        $fullEvidencePath = [IO.Path]::GetFullPath($EvidencePath)
        $parentDirectory = [IO.Path]::GetDirectoryName($fullEvidencePath)
        if (-not [IO.Directory]::Exists($parentDirectory)) { [void][IO.Directory]::CreateDirectory($parentDirectory) }
        $evidenceJson = ConvertTo-Json -InputObject $evidence -Depth 10
        [IO.File]::WriteAllText($fullEvidencePath, $evidenceJson, (New-Object Text.UTF8Encoding($false)))
        Write-Host "Evidence written to $fullEvidencePath"
    }
}

foreach ($cleanupError in $cleanupErrors) { Write-Warning $cleanupError }
if ($null -ne $failure) { throw "Order smoke test failed: $failure" }
if ($cleanupErrors.Count -gt 0) { throw 'Order checks passed but cleanup was incomplete. See warnings/evidence.' }
Write-Host "Order smoke test passed: $($checks.Count) checks; own demo records cleaned up."
