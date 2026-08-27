$ErrorActionPreference = 'Stop'

function Get-ExpectedCause($bankCode, $statusCode, $npciCode, $hasNotification) {
    if (-not $hasNotification) { return "notification_compliance_block" }
    if ($bankCode -in @("57","59","14","93") -or $npciCode -eq "U69" -or $statusCode -in @("BLOCKED","RISK_CHECK_FAILED")) { return "fraud_filter_block" }
    if ($bankCode -in @("05","12","41","43","54","62") -or $statusCode -in @("INVALID_CARD","DO_NOT_HONOUR")) { return "hard_decline" }
    if ($statusCode -in @("GATEWAY_ERROR","TIMEOUT","TECHNICAL_ERROR","NETWORK_ERROR") -or $bankCode -eq "96") { return "gateway_fault" }
    return "soft_decline"
}

$testCases = @(
    # Compliance Block
    @{ s="FAILED"; b=$null; n=$null; d="2026-08-28T10:00:00Z"; m=$null; amt=50000; name="Compliance1" },
    @{ s="MANDATE_REJECTED"; b=$null; n="U16"; d="2026-08-28T10:00:00Z"; m=$null; amt=10000; name="Compliance2" },
    
    # Fraud Block
    @{ s="FAILED"; b="57"; n=$null; d="2026-08-28T10:00:00Z"; m="2026-08-26T08:00:00Z"; amt=80000; name="Fraud1" },
    @{ s="BLOCKED"; b="59"; n="U69"; d="2026-08-28T10:00:00Z"; m="2026-08-26T08:00:00Z"; amt=150000; name="Fraud2" },

    # Hard Decline
    @{ s="INVALID_CARD"; b="05"; n=$null; d="2026-08-28T10:00:00Z"; m="2026-08-26T08:00:00Z"; amt=25000; name="Hard1" },
    @{ s="FAILED"; b="41"; n=$null; d="2026-08-28T10:00:00Z"; m="2026-08-26T08:00:00Z"; amt=35000; name="Hard2" },

    # Gateway Fault
    @{ s="TIMEOUT"; b=$null; n=$null; d="2026-08-28T10:00:00Z"; m="2026-08-26T08:00:00Z"; amt=10000; name="Gateway1" },
    @{ s="FAILED"; b="96"; n=$null; d="2026-08-28T10:00:00Z"; m="2026-08-26T08:00:00Z"; amt=75000; name="Gateway2" },

    # Soft Decline
    @{ s="FAILED"; b="51"; n=$null; d="2026-08-28T10:00:00Z"; m="2026-08-26T08:00:00Z"; amt=20000; name="Soft1" },
    @{ s="DECLINED"; b="91"; n=$null; d="2026-08-28T10:00:00Z"; m="2026-08-26T08:00:00Z"; amt=30000; name="Soft2" }
)

Write-Host "Starting Accuracy Test (N=$($testCases.Length))..."

$ts = [int][double]::Parse((Get-Date -UFormat %s))
$results = @{}

foreach ($i in 0..($testCases.Length-1)) {
    $tc = $testCases[$i]
    $txnId = "acc-$ts-$i"
    
    $payload = @{
        event = "payment.failed"
        payload = @{
            payment = @{
                entity = @{
                    id = $txnId
                    status_code = $tc.s
                    amount = $tc.amt
                    debit_scheduled_at = $tc.d
                }
            }
        }
    }
    if ($tc.b) { $payload.payload.payment.entity["acquirer_data"] = $tc.b }
    if ($tc.n) { $payload.payload.payment.entity["npci_txn_id"] = $tc.n }
    if ($tc.m) { $payload.payload.payment.entity["mandate_notification_sent_at"] = $tc.m }

    $json = $payload | ConvertTo-Json -Depth 5 -Compress
    
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:3001/api/v1/webhook" -Method POST -Body $json -ContentType "application/json" -UseBasicParsing
        $resp = $r.Content | ConvertFrom-Json
        $expected = Get-ExpectedCause -bankCode $tc.b -statusCode $tc.s -npciCode $tc.n -hasNotification ($null -ne $tc.m)
        $results[$resp.transaction_id] = @{ expected = $expected; name = $tc.name }
    } catch {
        Write-Host "Failed to ingest $txnId"
    }
}

Write-Host "Ingested $($results.Count) transactions. Waiting 15s for LLM processing..."
Start-Sleep -Seconds 15

$r = Invoke-WebRequest -Uri "http://localhost:3003/api/v1/classifications?limit=10" -UseBasicParsing
$data = ($r.Content | ConvertFrom-Json).data

$correct = 0
$total = 0

foreach ($d in $data) {
    if ($results.ContainsKey($d.transaction_id)) {
        $meta = $results[$d.transaction_id]
        $total++
        if ($d.cause -eq $meta.expected) {
            Write-Host "PASS: $($meta.name) -> $($d.cause) (Conf: $($d.confidence), L$($d.layer))" -ForegroundColor Green
            $correct++
        } else {
            Write-Host "FAIL: $($meta.name) -> Expected $($meta.expected) but got $($d.cause) (L$($d.layer))" -ForegroundColor Red
            Write-Host "      Reason: $($d.reasoning)" -ForegroundColor Yellow
        }
    }
}

$acc = ($correct / $total) * 100
Write-Host "`nFinal MVP Accuracy: $acc% ($correct/$total correct)" -ForegroundColor Cyan
