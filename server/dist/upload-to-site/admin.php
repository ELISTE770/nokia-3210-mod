<?php
/**
 * admin.php — owner's view. Open this from a desktop browser, not the phone.
 *
 * Shows every account, its usage counters and the full event log across all
 * users, which is where you look when someone says "it stopped working".
 * API keys are never printed in full.
 */

declare(strict_types=1);

require __DIR__ . '/lib.php';

session_set_cookie_params(['httponly' => true, 'samesite' => 'Lax']);
session_start();

$err = '';
if (($_POST['pw'] ?? '') !== '') {
    if (hash_equals(ADMIN_PASSWORD, (string) $_POST['pw'])) {
        $_SESSION['admin'] = true;
        log_event('admin', 'login_ok');
    } else {
        $err = 'סיסמה שגויה.';
        log_event('admin', 'login_fail');
    }
}
if (isset($_GET['out'])) {
    unset($_SESSION['admin']);
}
$in = !empty($_SESSION['admin']);

if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(16));
}
$csrf = (string) $_SESSION['csrf_token'];

if ($in && ($_POST['drop'] ?? '') !== '') {
    $token = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($_SESSION['csrf_token'] ?? '', $token)) {
        $err = 'פג תוקף הטופס (שגיאת CSRF). רענן ונסה שוב.';
    } else {
        $id = (string) $_POST['drop'];
        if (account_load($id) !== null) {
            session_end_all($id);
            store_delete('accounts', $id);
            log_event('admin', 'account_deleted', ['account' => $id]);
        }
    }
}

function mask(string $key): string
{
    $n = strlen($key);
    return $n <= 10 ? str_repeat('*', $n) : substr($key, 0, 6) . str_repeat('*', 6) . substr($key, -4);
}

header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store');
?>
<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="utf-8" />
<title>ניהול</title>
<style>
body{font-family:system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;line-height:1.55}
table{border-collapse:collapse;width:100%;margin:.6rem 0}
th,td{border-bottom:1px solid #ddd;padding:.4rem .5rem;text-align:right;font-size:.9rem}
th{background:#f4f4f4}
code{font-family:ui-monospace,monospace;font-size:.85rem}
.err{color:#c5221f}.dim{color:#666;font-size:.85rem}
.fail{background:#fce8e6}
</style>
</head>
<body>
<h1>ניהול</h1>

<?php if (!$in): ?>
  <?php if ($err !== ''): ?><p class="err"><?= e($err) ?></p><?php endif; ?>
  <form method="post">
    <p>סיסמת מנהל: <input type="password" name="pw" /> <input type="submit" value="כניסה" /></p>
  </form>
<?php else: ?>

  <?php if (ADMIN_PASSWORD === 'CHANGE-ME-ADMIN'): ?>
    <div style="background:#fce8e6;border:1px solid #c5221f;padding:10px;border-radius:4px;margin-bottom:1rem;">
      <strong class="err">אזהרת אבטחה:</strong> סיסמת המנהל עדיין מוגדרת כברירת המחדל (<code>CHANGE-ME-ADMIN</code>).
      יש לקבוע סיסמה ייעודית במשתנה הסביבה <code>GEMINI_ADMIN_PASSWORD</code> או בקובץ <code>lib.php</code>.
    </div>
  <?php endif; ?>
  <?php if ($err !== ''): ?><p class="err"><?= e($err) ?></p><?php endif; ?>

  <h2>חשבונות</h2>
  <?php $ids = store_list('accounts'); ?>
  <p class="dim"><?= count($ids) ?> חשבונות</p>
  <table>
    <tr><th>מזהה</th><th>שם</th><th>מפתח</th><th>מודל</th><th>שאלות</th>
        <th>כשלים</th><th>נוצר</th><th>פעילות אחרונה</th><th></th></tr>
    <?php foreach ($ids as $id): $a = store_read('accounts', $id); if (!$a) continue; ?>
    <tr>
      <td><code><?= e((string) $a['id']) ?></code></td>
      <td><?= e((string) ($a['label'] ?? '')) ?></td>
      <td><code><?= e(mask((string) ($a['api_key'] ?? ''))) ?></code></td>
      <td class="dim"><?= e((string) ($a['model'] ?? '')) ?></td>
      <td><?= (int) ($a['calls'] ?? 0) ?></td>
      <td<?= (int) ($a['errors'] ?? 0) > 0 ? ' class="fail"' : '' ?>><?= (int) ($a['errors'] ?? 0) ?></td>
      <td class="dim"><?= e(substr((string) ($a['created'] ?? ''), 0, 10)) ?></td>
      <td class="dim"><?= e(str_replace('T', ' ', substr((string) ($a['last_seen'] ?? ''), 0, 16))) ?></td>
      <td><form method="post" onsubmit="return confirm('למחוק את <?= e((string) $a['id']) ?>?')">
        <input type="hidden" name="csrf" value="<?= e($csrf) ?>" />
        <input type="hidden" name="drop" value="<?= e((string) $a['id']) ?>" />
        <input type="submit" value="מחק" /></form></td>
    </tr>
    <?php endforeach; ?>
  </table>

  <h2>יומן</h2>
  <?php
    $days = log_days();
    $day  = (string) ($_GET['d'] ?? ($days[0] ?? gmdate('Y-m-d')));
    $rows = log_read($day, null, 300);
  ?>
  <p>
  <?php foreach (array_slice($days, 0, 14) as $d): ?>
    <a href="?d=<?= e($d) ?>"><?= e($d) ?></a>&#160;
  <?php endforeach; ?>
  </p>
  <table>
    <tr><th>שעה</th><th>שלב</th><th>תוצאה</th><th>חשבון</th><th>זמן</th>
        <th>טוקנים</th><th>פרטים</th></tr>
    <?php foreach ($rows as $r): $bad = in_array($r['result'] ?? '', ['fail','bad_key','bad_credentials','blocked','login_fail'], true); ?>
    <tr<?= $bad ? ' class="fail"' : '' ?>>
      <td class="dim"><?= e(substr((string) ($r['ts'] ?? ''), 11, 8)) ?></td>
      <td><?= e((string) ($r['stage'] ?? '')) ?></td>
      <td><?= e((string) ($r['result'] ?? '')) ?></td>
      <td><code><?= e((string) ($r['account'] ?? '')) ?></code></td>
      <td class="dim"><?= isset($r['ms']) ? (int) $r['ms'] . 'ms' : '' ?></td>
      <td class="dim"><?= isset($r['tokens']) ? (int) $r['tokens'] : '' ?></td>
      <td class="dim"><?= e((string) ($r['error'] ?? ($r['status'] ?? ''))) ?></td>
    </tr>
    <?php endforeach; ?>
  </table>
  <?php if (!$rows): ?><p class="dim">אין רשומות ליום הזה.</p><?php endif; ?>

  <p><a href="?out=1">יציאה</a></p>
<?php endif; ?>
</body>
</html>
