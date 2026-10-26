<?php
/**
 * Gemini for Nokia 3210 4G (UMS9117 / MOCOR) — multi-user front end.
 *
 * Constraints this file is built around, all measured from the phone firmware:
 *   - No JavaScript engine worth using -> every action is a plain form POST.
 *   - XHTML/WML renderer with libcss -> simple block markup, no modern CSS.
 *   - 240x320 screen -> single narrow column, short lines.
 *   - mbedTLS 2.6, RSA-only ciphersuites, one GoDaddy root CA -> plain HTTP.
 *   - Limited RAM -> the transcript never travels to the phone. Conversation
 *     state lives on Google's side via previous_interaction_id.
 *
 * The phone sends nothing that identifies it — no IMEI, no serial, no MSISDN
 * header; every 3210 looks identical on the wire. So identity is issued by us:
 * a session cookie the browser carries back. Lose the cookie and the only way
 * back in is the account id plus its PIN, which is exactly the "new device
 * needs a code" rule.
 */

declare(strict_types=1);

require __DIR__ . '/lib.php';

$sess = session_current();
$acc  = $sess['_account'] ?? null;
$page = (string) ($_GET['p'] ?? '');
$post = $_SERVER['REQUEST_METHOD'] === 'POST';

$error  = '';
$notice = '';

// ------------------------------------------------------------- actions ----

if ($post && $page === 'register') {
    $key   = trim((string) ($_POST['key'] ?? ''));
    $pin   = trim((string) ($_POST['pin'] ?? ''));
    $label = utf8_cut(trim((string) ($_POST['label'] ?? '')), 40);

    if ($key === '') {
        $error = 'חסר מפתח API.';
    } elseif (!preg_match('/^\d{4,8}$/', $pin)) {
        $error = 'הקוד חייב להיות 4 עד 8 ספרות.';
    } else {
        $probe = gemini_validate_key($key);
        if (!$probe['ok']) {
            $error = 'המפתח נדחה על ידי Google: ' . $probe['error'];
            log_event('register', 'bad_key', ['status' => $probe['status']]);
        } else {
            $acc = account_create($key, $pin, $label);
            session_start_for($acc['id'], $label);
            $notice = 'החשבון נוצר. רשום לעצמך את המזהה והקוד.';
            $page   = 'welcome';
        }
    }
}

if ($post && $page === 'login') {
    $id  = strtoupper(trim((string) ($_POST['id'] ?? '')));
    $pin = trim((string) ($_POST['pin'] ?? ''));

    if (login_blocked($id)) {
        $error = 'יותר מדי ניסיונות. נסה שוב בעוד רבע שעה.';
        log_event('login', 'blocked', ['account' => $id]);
    } else {
        $cand = account_load($id);
        if ($cand === null || !password_verify($pin, (string) $cand['pin_hash'])) {
            login_fail($id);
            $error = 'מזהה או קוד שגויים.';
            log_event('login', 'bad_credentials', ['account' => $id]);
        } else {
            login_ok($id);
            session_start_for($cand['id'], utf8_cut(trim((string) ($_POST['device'] ?? '')), 40));
            $acc  = $cand;
            $sess = session_current();
            $notice = 'התחברת.';
            $page = '';
        }
    }
}

if ($page === 'logout' && $sess !== null) {
    session_end((string) $sess['_key']);
    log_event('session', 'ended', ['account' => $acc['id'] ?? '-']);
    header('Location: ?p=login');
    exit;
}

if ($post && $page === 'logout-all' && $acc !== null) {
    $n = session_end_all((string) $acc['id']);
    header('Location: ?p=login&msg=' . rawurlencode("נותקו $n מכשירים."));
    exit;
}

if ($post && $page === 'settings' && $acc !== null) {
    $model = (string) ($_POST['model'] ?? '');
    if (isset(MODELS[$model])) {
        $acc['model'] = $model;
        account_save($acc);
        $notice = 'המודל עודכן.';
        log_event('settings', 'model_changed', ['account' => $acc['id'], 'model' => $model]);
    } else {
        $error = 'מודל לא מוכר.';
    }
    $newKey = trim((string) ($_POST['key'] ?? ''));
    if ($newKey !== '') {
        $probe = gemini_validate_key($newKey);
        if ($probe['ok']) {
            $acc['api_key'] = $newKey;
            account_save($acc);
            $notice = 'המפתח הוחלף.';
            log_event('settings', 'key_changed', ['account' => $acc['id']]);
        } else {
            $error = 'המפתח החדש נדחה: ' . $probe['error'];
        }
    }
}

// ---------------------------------------------------------------- chat ----

$question = '';
$answer   = '';
$prev     = '';

if ($post && $page === '' && $acc !== null) {
    $prev     = (string) ($_POST['prev'] ?? '');
    $question = utf8_cut(trim((string) ($_POST['q'] ?? '')), MAX_INPUT_CHARS);

    if ($question !== '') {
        $res = gemini_call((string) $acc['api_key'], (string) ($acc['model'] ?? DEFAULT_MODEL),
                           $question, $prev);
        log_event('ask', $res['ok'] ? 'ok' : 'fail', [
            'account' => $acc['id'],
            'model'   => $acc['model'] ?? DEFAULT_MODEL,
            'status'  => $res['status'],
            'ms'      => $res['ms'],
            'tokens'  => $res['usage']['total_tokens'] ?? null,
            'error'   => $res['ok'] ? null : $res['error'],
        ]);
        account_touch($acc, !$res['ok']);
        if ($res['ok']) {
            $answer = $res['text'];
            $prev   = $res['id'];
        } else {
            $error = $res['error'];
        }
    }
}

if (isset($_GET['new'])) {
    $prev = $question = $answer = '';
}
if (isset($_GET['msg'])) {
    $notice = utf8_cut((string) $_GET['msg'], 120);
}

// If there is no session, the only pages that make sense are login/register.
if ($acc === null && !in_array($page, ['register', 'welcome'], true)) {
    $page = 'login';
}

header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store');
?>
<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Gemini</title>
<style type="text/css">
body { font-family: sans-serif; font-size: 14px; margin: 4px; }
h1   { font-size: 16px; margin: 2px 0 6px 0; }
h2   { font-size: 15px; margin: 10px 0 4px 0; }
p    { margin: 4px 0; }
.q   { color: #444; }
.a   { border-top: 1px solid #999; padding-top: 4px; }
.err { border: 1px solid #900; padding: 3px; }
.ok  { border: 1px solid #090; padding: 3px; }
.id  { font-size: 20px; letter-spacing: 2px; }
.nav { border-top: 1px solid #ccc; margin-top: 10px; padding-top: 5px; font-size: 13px; }
.dim { color: #666; font-size: 12px; }
textarea, input, select { width: 96%; font-size: 14px; }
</style>
</head>
<body>

<h1>Gemini</h1>

<?php if ($error !== ''): ?>
<p class="err"><?= e($error) ?></p>
<?php endif; ?>
<?php if ($notice !== ''): ?>
<p class="ok"><?= e($notice) ?></p>
<?php endif; ?>


<?php if ($page === 'welcome' && $acc !== null): ?>
  <h2>שמור את הפרטים האלה</h2>
  <p>המזהה שלך:</p>
  <p class="id"><?= e((string) $acc['id']) ?></p>
  <p class="dim">רשום אותו על נייר יחד עם הקוד שבחרת.
  בלעדיהם אי אפשר להתחבר ממכשיר אחר, ואי אפשר לשחזר אותם.</p>
  <p><a href="./">התחל</a></p>


<?php elseif ($page === 'login'): ?>
  <h2>כניסה</h2>
  <form method="post" action="?p=login" accept-charset="utf-8">
  <p>מזהה:<br /><input type="text" name="id" /></p>
  <p>קוד:<br /><input type="password" name="pin" /></p>
  <p>שם המכשיר (לא חובה):<br /><input type="text" name="device" /></p>
  <p><input type="submit" value="כניסה" /></p>
  </form>
  <p class="dim">אין לך מזהה? <a href="?p=register">הרשמה</a></p>


<?php elseif ($page === 'register'): ?>
  <h2>הרשמה</h2>
  <p class="dim">צריך מפתח API משלך מ-Google AI Studio.
  השימוש נזקף למכסה שלך בלבד.</p>
  <form method="post" action="?p=register" accept-charset="utf-8">
  <p>מפתח API:<br /><input type="text" name="key" /></p>
  <p>בחר קוד, 4 עד 8 ספרות:<br /><input type="password" name="pin" /></p>
  <p>שם לזיהוי (לא חובה):<br /><input type="text" name="label" /></p>
  <p><input type="submit" value="צור חשבון" /></p>
  </form>
  <p class="dim">המפתח נבדק מול Google לפני השמירה.</p>
  <p><a href="?p=login">כבר יש לי מזהה</a></p>


<?php elseif ($page === 'settings' && $acc !== null): ?>
  <h2>הגדרות</h2>
  <form method="post" action="?p=settings" accept-charset="utf-8">
  <p>מודל:<br />
  <select name="model">
  <?php foreach (MODELS as $m => $lbl): ?>
    <option value="<?= e($m) ?>"<?= ($acc['model'] ?? '') === $m ? ' selected="selected"' : '' ?>>
      <?= e($lbl) ?>
    </option>
  <?php endforeach; ?>
  </select></p>
  <p>מפתח API חדש (השאר ריק כדי לא לשנות):<br /><input type="text" name="key" /></p>
  <p><input type="submit" value="שמור" /></p>
  </form>

  <h2>מכשירים מחוברים</h2>
  <?php foreach (sessions_of((string) $acc['id']) as $s): ?>
    <p><?= e(($s['device'] ?? '') !== '' ? (string) $s['device'] : 'ללא שם') ?>
    <span class="dim"><?= e(substr((string) $s['created'], 0, 10)) ?><?php
      if (isset($sess['_key']) && $s['_key'] === $sess['_key']) { echo ' — זה המכשיר הנוכחי'; } ?></span></p>
  <?php endforeach; ?>
  <form method="post" action="?p=logout-all">
  <p><input type="submit" value="נתק את כל המכשירים" /></p>
  </form>

  <p class="dim">מזהה: <?= e((string) $acc['id']) ?> —
  <?= (int) ($acc['calls'] ?? 0) ?> שאלות, <?= (int) ($acc['errors'] ?? 0) ?> כשלים</p>
  <p><a href="./">חזרה</a></p>


<?php elseif ($page === 'log' && $acc !== null): ?>
  <h2>יומן</h2>
  <?php
    $days = log_days();
    $day  = (string) ($_GET['d'] ?? ($days[0] ?? gmdate('Y-m-d')));
    $rows = log_read($day, (string) $acc['id'], 40);
  ?>
  <p class="dim"><?= e($day) ?></p>
  <?php if (!$rows): ?><p class="dim">אין רשומות ליום הזה.</p><?php endif; ?>
  <?php foreach ($rows as $r): ?>
    <p><?= e(substr((string) ($r['ts'] ?? ''), 11, 8)) ?>
       <?= e((string) ($r['stage'] ?? '')) ?>
       — <?= e((string) ($r['result'] ?? '')) ?>
       <?php if (!empty($r['ms'])): ?><span class="dim"><?= (int) $r['ms'] ?>ms</span><?php endif; ?>
       <?php if (!empty($r['error'])): ?><br /><span class="dim"><?= e((string) $r['error']) ?></span><?php endif; ?>
    </p>
  <?php endforeach; ?>
  <?php foreach (array_slice($days, 0, 7) as $d): ?>
    <a href="?p=log&amp;d=<?= e($d) ?>"><?= e(substr($d, 5)) ?></a>&#160;
  <?php endforeach; ?>
  <p><a href="./">חזרה</a></p>


<?php else: /* ---------------------------------------------------- chat -- */ ?>
  <?php if ($answer !== ''): ?>
    <p class="q"><?= e($question) ?></p>
    <p class="a"><?= nl2br(e($answer)) ?></p>
  <?php endif; ?>

  <form method="post" action="./" accept-charset="utf-8">
  <p><textarea name="q" rows="3"></textarea></p>
  <input type="hidden" name="prev" value="<?= e($prev) ?>" />
  <p><input type="submit" value="שלח" /></p>
  </form>

  <div class="nav">
  <?php if ($prev !== ''): ?><a href="?new=1">שיחה חדשה</a> | <?php endif; ?>
  <a href="?p=settings">הגדרות</a> |
  <a href="?p=log">יומן</a> |
  <a href="?p=logout">יציאה</a>
  </div>
  <p class="dim"><?= e((string) $acc['id']) ?> · <?= e(model_label((string) ($acc['model'] ?? DEFAULT_MODEL))) ?></p>
<?php endif; ?>

</body>
</html>
