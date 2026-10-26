$ErrorActionPreference='Continue'
$SP  = "C:\Users\Eli\AppData\Local\Temp\claude\C--Users-Eli-OneDrive---PCMASTER-Desktop----------------\e6465429-4442-489a-9911-a889f3277a8f\scratchpad"
$APP = 'http://127.0.0.1:8080/'
$DATA = Join-Path $SP 'data'

$pass=0; $fail=0
function Check($n,$c,$d=''){ if($c){$script:pass++;"  [PASS] $n"} else {$script:fail++;"  [FAIL] $n  $d"} }

# a "device" = its own cookie jar
function New-Device { [Microsoft.PowerShell.Commands.WebRequestSession]::new() }

function Req($dev,$url,$fields=$null){
  $p=@{Uri=($APP+$url); WebSession=$dev; TimeoutSec=40; UseBasicParsing=$true}
  if($fields){
    $pairs = foreach($k in $fields.Keys){ "$([uri]::EscapeDataString($k))=$([uri]::EscapeDataString([string]$fields[$k]))" }
    $p.Method='Post'; $p.Body=[Text.Encoding]::UTF8.GetBytes(($pairs -join '&'))
    $p.ContentType='application/x-www-form-urlencoded; charset=utf-8'
  }
  try { $r=Invoke-WebRequest @p; [Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray()) }
  catch { "HTTPERR $($_.Exception.Message)" }
}

$A = New-Device; $B = New-Device

"=== 1. no session -> login page ==="
$h = Req $A ''
Check 'shows login'        ($h -match 'כניסה' -and $h -match 'name="id"')
Check 'no chat box'        ($h -notmatch '<textarea')
Check 'register link'      ($h -match 'p=register')

"=== 2. register rejects a bad PIN before touching Google ==="
$h = Req $A '?p=register' @{ key='AQ.MOCKKEY-AAA'; pin='12'; label='test' }
Check 'pin too short'      ($h -match '4 עד 8 ספרות')

"=== 3. register rejects a key Google refuses ==="
$h = Req $A '?p=register' @{ key='BADKEY'; pin='1234'; label='test' }
Check 'bad key rejected'   ($h -match 'נדחה')
Check 'no account created' ((Get-ChildItem (Join-Path $DATA 'accounts') -ErrorAction SilentlyContinue).Count -eq 0)

"=== 4. successful registration ==="
$h = Req $A '?p=register' @{ key='AQ.MOCKKEY-AAA'; pin='4321'; label='מכשיר של אלי'; email='eli@example.com' }
Check 'welcome shown'      ($h -match 'שמור את הפרטים')
$ids = [regex]::Matches($h,'<p class="id">([A-Z0-9-]+)</p>')
$id1 = if($ids.Count -ge 1){$ids[0].Groups[1].Value}else{''}
$rec1 = if($ids.Count -ge 2){$ids[1].Groups[1].Value}else{''}
Check 'recovery code shown' ($rec1 -match '^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$') "got '$rec1'"
Check 'id issued'          ($id1 -match '^[A-Z0-9]{8}$') "got '$id1'"
Check 'no ambiguous chars' ($id1 -notmatch '[01OIL]') "id=$id1"
$accFile = Join-Path $DATA "accounts\$id1.json"
Check 'account persisted'  (Test-Path $accFile)

"=== 5. device A can now chat ==="
$h = Req $A '' @{ q='מה בירת יפן?'; prev='' }
Check 'answer rendered'    ($h -match 'class="a"')
Check 'nav visible'        ($h -match 'p=settings' -and $h -match 'p=logout')
$prev = if($h -match 'name="prev" value="([^"]*)"'){$Matches[1]}else{''}
Check 'prev captured'      ($prev -ne '')
$h = Req $A '' @{ q='ומה במדריד?'; prev=$prev }
$req = Get-Content (Join-Path $SP 'mock\last_request.json') -Raw | ConvertFrom-Json
Check 'prev chained'       ($req.body.previous_interaction_id -eq $prev)
Check "used A's key"       ($req.headers.'x-goog-api-key' -eq 'AQ.MOCKKEY-AAA')

"=== 6. device B has no cookie -> must log in ==="
$h = Req $B ''
Check 'B sees login'       ($h -match 'name="id"' -and $h -notmatch '<textarea')

"=== 7. correct id but WRONG code is refused ==="
$h = Req $B '?p=login' @{ id=$id1; pin='9999'; device='B' }
Check 'wrong pin refused'  ($h -match 'שגויים')
Check 'still no chat'      ($h -notmatch '<textarea')

"=== 8. id + code from a new device works ==="
$h = Req $B '?p=login' @{ id=$id1; pin='4321'; device='מכשיר שני' }
Check 'B logged in'        ($h -match '<textarea')
$h = Req $B '?p=settings'
Check 'B sees 2 devices'   (([regex]::Matches($h,'מכשיר')).Count -ge 2)

"=== 9. brute force is throttled ==="
$C = New-Device
1..6 | ForEach-Object { $null = Req $C '?p=login' @{ id=$id1; pin='0000' } }
$h = Req $C '?p=login' @{ id=$id1; pin='4321' }
Check 'blocked after 5'    ($h -match 'יותר מדי ניסיונות')
Check 'block beats a correct pin' ($h -notmatch '<textarea')
$rl = Get-ChildItem (Join-Path $DATA 'ratelimit') -ErrorAction SilentlyContinue
Check 'throttle keyed by ip+account, not account' ($rl.BaseName -notcontains $id1) "files: $($rl.BaseName -join ',')"

"=== 10. a second account is fully isolated ==="
$D = New-Device
$h = Req $D '?p=register' @{ key='AQ.MOCKKEY-BBB'; pin='5555'; label='שני' }
$id2 = if($h -match '<p class="id">([A-Z0-9]+)</p>'){$Matches[1]}else{''}
Check 'second id differs'  ($id2 -ne $id1 -and $id2 -ne '')
$null = Req $D '' @{ q='שאלה'; prev='' }
$req = Get-Content (Join-Path $SP 'mock\last_request.json') -Raw | ConvertFrom-Json
Check "used B's key"       ($req.headers.'x-goog-api-key' -eq 'AQ.MOCKKEY-BBB')

"=== 11. model switching ==="
$h = Req $D '?p=settings' @{ model='gemini-3.5-flash-lite' }
Check 'model saved'        ($h -match 'המודל עודכן')
$null = Req $D '' @{ q='שאלה'; prev='' }
$req = Get-Content (Join-Path $SP 'mock\last_request.json') -Raw | ConvertFrom-Json
Check 'model actually used' ($req.body.model -eq 'gemini-3.5-flash-lite') "got $($req.body.model)"
$h = Req $D '?p=settings' @{ model='evil-model' }
Check 'unknown model rejected' ($h -match 'לא מוכר')

"=== 12. sign out ==="
$h = Req $B '?p=logout'
Check 'B back to login'    ($h -match 'name="id"')
$h = Req $A ''
Check 'A still signed in'  ($h -match '<textarea')

"=== 13. sign out all devices ==="
$null = Req $A '?p=logout-all' @{ x='1' }
Check 'A signed out too'   ((Req $A '') -match 'name="id"')

"=== 14. log page ==="
# fresh account: test 9 deliberately throttled $id1 from this address
$E = New-Device
$h = Req $E '?p=register' @{ key='AQ.MOCKKEY-CCC'; pin='7777'; label='יומן' }
$ids = [regex]::Matches($h,'<p class="id">([A-Z0-9-]+)</p>')
$id3  = if($ids.Count -ge 1){$ids[0].Groups[1].Value}else{''}
$rec3 = if($ids.Count -ge 2){$ids[1].Groups[1].Value}else{''}
Check 'third account made' ($id3 -match '^[A-Z0-9]{8}$')
$null = Req $E '' @{ q='שאלה ליומן'; prev='' }
$h = Req $E '?p=log'
Check 'log renders'        ($h -match 'יומן')
Check 'shows ask events'   ($h -match 'ask')

"=== 15. failures are logged with a reason ==="
$null = Req $E '' @{ q='TRIGGER_HTTP_ERROR'; prev='' }
$today = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd')
$logs = Get-Content (Join-Path $DATA "logs\$today.jsonl") -ErrorAction SilentlyContinue
Check 'fail line written'  ($logs -match '"result":"fail"')
Check 'reason recorded'    ($logs -match 'Quota exceeded')
Check 'key never logged'   (-not ($logs -match 'MOCKKEY'))

"=== 16. secrets are not exposed to the browser ==="
$h = Req $E '?p=settings'
Check 'api key not shown'  ($h -notmatch 'MOCKKEY')
Check 'pin hash not shown' ($h -notmatch '\$2y\$')

"=== 17. no PHP errors anywhere ==="
$all = @((Req $E ''),(Req $E '?p=settings'),(Req $E '?p=log'),(Req $B ''),(Req $B '?p=register')) -join "`n"
Check 'no Warning'         ($all -notmatch 'Warning:')
Check 'no Notice'          ($all -notmatch 'Notice:')
Check 'no Fatal'           ($all -notmatch 'Fatal error')
Check 'no Deprecated'      ($all -notmatch 'Deprecated:')

# $id1 was deliberately throttled in test 9, so these use the clean $id3
"=== 18. recovery code is not guessable and not replayable ==="
$F = New-Device
$h = Req $F '?p=recover' @{ id=$id3; code='AAAA-BBBB-CCCC-DDDD'; pin='1111' }
Check 'wrong recovery refused' ($h -match 'שגויים')
$h = Req $F '?p=recover' @{ id=$id3; code=$rec3; pin='1111' }
Check 'recovery works'         ($h -match 'שמור את הפרטים')
$ids = [regex]::Matches($h,'<p class="id">([A-Z0-9-]+)</p>')
$rec3b = if($ids.Count -ge 2){$ids[1].Groups[1].Value}else{''}
Check 'fresh code issued'      ($rec3b -ne '' -and $rec3b -ne $rec3)
$h = Req (New-Device) '?p=recover' @{ id=$id3; code=$rec3; pin='2222' }
Check 'old code now dead'      ($h -match 'שגויים')

"=== 19. recovery accepts the code without dashes and in lower case ==="
$G = New-Device
$h = Req $G '?p=recover' @{ id=$id3; code=($rec3b -replace '-','').ToLower(); pin='3333' }
Check 'normalised form accepted' ($h -match 'שמור את הפרטים')
$ids = [regex]::Matches($h,'<p class="id">([A-Z0-9-]+)</p>')
$rec3c = if($ids.Count -ge 2){$ids[1].Groups[1].Value}else{''}

"=== 20. recovery revokes every existing session ==="
$H = New-Device
$null = Req $H '?p=login' @{ id=$id3; pin='3333' }
Check 'new pin works'          ((Req $H '') -match '<textarea')
$null = Req (New-Device) '?p=recover' @{ id=$id3; code=$rec3c; pin='4444' }
Check 'earlier session killed' ((Req $H '') -match 'name="id"')

"=== 21. daily quota ==="
$acctPath = Join-Path $DATA "accounts\$id3.json"
$j = Get-Content $acctPath -Raw | ConvertFrom-Json
$j.day = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd')
$j.day_calls = 300
$j | ConvertTo-Json -Depth 5 | Set-Content $acctPath -Encoding UTF8
$I = New-Device
$null = Req $I '?p=login' @{ id=$id3; pin='4444' }
$h = Req $I '' @{ q='שאלה מעבר למכסה'; prev='' }
Check 'quota enforced'         ($h -match 'מכסה היומית')
Check 'no answer served'       ($h -notmatch 'class="a"')

"=== 22. registration throttle closes the key-testing oracle ==="
$J = New-Device
$blocked = $false
1..8 | ForEach-Object {
  $r = Req $J '?p=register' @{ key="AQ.MOCKKEY-T$_"; pin='9876' }
  if ($r -match 'יותר מדי ניסיונות הרשמה') { $script:blocked = $true }
}
Check 'registration throttled' $blocked

"`n============================"
"PASSED: $pass   FAILED: $fail"
