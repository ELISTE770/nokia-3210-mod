<?php
/**
 * check.php — deployment diagnostic.
 *
 * Drop this next to index.php, open it in a desktop browser, fix whatever it
 * reports, then DELETE IT. It prints server paths and makes a billed API call,
 * so it is not something to leave reachable.
 */

declare(strict_types=1);

require __DIR__ . '/lib.php';

$rows = [];

/** @param string $level 'must' blocks the run, 'nice' is informational only. */
function row(string $label, bool $ok, string $detail, string $fix = '', string $level = 'must'): void
{
    global $rows;
    $rows[] = compact('label', 'ok', 'detail', 'fix', 'level');
}

// --- environment ---------------------------------------------------------

row('גרסת PHP', PHP_VERSION_ID >= 80000, PHP_VERSION,
    'צריך PHP 8.0 ומעלה. ב-cPanel תחת "Select PHP Version".');

row('הרחבת curl', extension_loaded('curl'),
    extension_loaded('curl') ? (curl_version()['version'] ?? 'טעונה') : 'לא טעונה',
    'ב-cPanel: Select PHP Version -> Extensions -> curl.');

row('הרחבת mbstring', extension_loaded('mbstring'),
    extension_loaded('mbstring') ? 'טעונה' : 'לא טעונה — לא נורא, יש נתיב חלופי',
    '', 'nice');

// --- paths ---------------------------------------------------------------

row('התיקייה שהדף רץ בה', true, __DIR__, '', 'nice');

$accountHome = '';
$probe = __DIR__;
while ($probe !== '' && $probe !== DIRECTORY_SEPARATOR) {
    $parent = dirname($probe);
    if (basename($parent) === 'home') { $accountHome = $probe; break; }
    if ($parent === $probe) { break; }
    $probe = $parent;
}
if ($accountHome !== '') {
    row('תיקיית החשבון שלך', true, $accountHome, '', 'nice');
}

// --- data directory ------------------------------------------------------

$dataOk = false;
try {
    $probeDir = store_dir('accounts');
    $tmp = $probeDir . '/.write-probe';
    $dataOk = @file_put_contents($tmp, 'x') !== false;
    @unlink($tmp);
} catch (Throwable $ex) {
    $dataOk = false;
}
row('תיקיית הנתונים קיימת וניתנת לכתיבה', $dataOk, DATA_DIR,
    'ודא ש-DATA_DIR ב-lib.php מצביע לנתיב שאפשר לכתוב אליו. הקוד יוצר אותו לבד אם ההרשאות מאפשרות.');

$docRoot = realpath($_SERVER['DOCUMENT_ROOT'] ?? '') ?: realpath(__DIR__);
$dataReal = realpath(DATA_DIR) ?: '';
$dataExposed = $docRoot !== '' && $dataReal !== '' && str_starts_with($dataReal, $docRoot);
row('הנתונים מחוץ לתיקייה הציבורית', !$dataExposed,
    $dataExposed ? 'הנתונים נגישים מהדפדפן — מפתחות המשתמשים חשופים' : 'מוגן',
    'העבר את DATA_DIR אל ' . ($accountHome !== '' ? $accountHome . '/gemini-data' : 'מחוץ ל-public_html'));

// --- admin password ------------------------------------------------------

row('סיסמת מנהל שונתה', ADMIN_PASSWORD !== 'CHANGE-ME-ADMIN',
    ADMIN_PASSWORD !== 'CHANGE-ME-ADMIN' ? 'הוגדרה' : 'עדיין ברירת המחדל',
    'שנה את ADMIN_PASSWORD ב-lib.php, אחרת כל אחד ייכנס ל-admin.php.');

// --- outbound connectivity ----------------------------------------------

if (extension_loaded('curl')) {
    $ch = curl_init(API_URL);
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => '{}',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
    ]);
    $raw    = curl_exec($ch);
    $errMsg = curl_error($ch);
    $status = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);

    if ($errMsg !== '') {
        row('חיבור לשרתי Google', false, $errMsg,
            str_contains($errMsg, 'certificate')
                ? 'לשרת חסרה חבילת תעודות שורש. בקש מהתמיכה לעדכן את curl.cainfo.'
                : 'ייתכן שהאחסון חוסם יציאה החוצה. פנה לתמיכה.');
    } else {
        // Without a key Google answers 400/401/403 — any of them proves we got there.
        row('חיבור לשרתי Google', $status > 0, 'הגיע, HTTP ' . $status,
            'לא התקבלה תשובה מהשרת.');
    }
}

// --- accounts ------------------------------------------------------------

if ($dataOk) {
    $n = count(store_list('accounts'));
    row('חשבונות רשומים', true, (string) $n . ' חשבונות', '', 'nice');
}

$blockers = array_filter($rows, fn($r) => !$r['ok'] && $r['level'] === 'must');
$allOk = !$blockers;

header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store');
?>
<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="utf-8" />
<title>בדיקת התקנה</title>
<style>
body{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;line-height:1.6}
table{border-collapse:collapse;width:100%}
td{border-bottom:1px solid #ddd;padding:.55rem .4rem;vertical-align:top}
.s{width:2.2rem;font-size:1.15rem}
.ok{color:#137333}.bad{color:#c5221f}.info{color:#8a8a8a}
.d{color:#555;font-family:ui-monospace,monospace;font-size:.88rem;word-break:break-all}
.f{color:#a15c00;font-size:.88rem}
.banner{padding:.8rem 1rem;border-radius:6px;margin-bottom:1.2rem}
.go{background:#e6f4ea;color:#137333}.no{background:#fce8e6;color:#c5221f}
</style>
</head>
<body>
<h1>בדיקת התקנה</h1>

<div class="banner <?= $allOk ? 'go' : 'no' ?>">
<?= $allOk ? 'הכול תקין. מחק את הקובץ הזה מהשרת ופתח את index.php.'
           : 'יש בעיות פתוחות — ראה את השורות המסומנות למטה.' ?>
</div>

<table>
<?php foreach ($rows as $r): ?>
<?php
  if ($r['ok'])                   { $cls = 'ok';   $mark = '✓'; }
  elseif ($r['level'] === 'nice') { $cls = 'info'; $mark = '–'; }
  else                            { $cls = 'bad';  $mark = '✕'; }
?>
<tr>
  <td class="s <?= $cls ?>"><?= $mark ?></td>
  <td>
    <strong><?= e($r['label']) ?></strong><br />
    <span class="d"><?= e($r['detail']) ?></span>
    <?php if (!$r['ok'] && $r['fix'] !== ''): ?>
      <br /><span class="f"><?= e($r['fix']) ?></span>
    <?php endif; ?>
  </td>
</tr>
<?php endforeach; ?>
</table>

<p><strong>אחרי שהכול ירוק — מחק את check.php מהשרת.</strong></p>
</body>
</html>
