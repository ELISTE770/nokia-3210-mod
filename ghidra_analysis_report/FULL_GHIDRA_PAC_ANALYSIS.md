# ניתוח מלא של קובצי ה-PAC ב-Ghidra (Nokia 3210 4G / Unisoc UMS9117)

## 1. רקע ומבנה קובץ ה-PAC (קונטיינר קושחה)

קובץ PAC (`3210.pac`) אינו קובץ הפעלה בינארי בודד, אלא **ארכיב קושחה קנייני** של חברת Unisoc / Spreadtrum (בגרסה `BP_R1.0.0`, מוצר `UMS9117`, קושחה `MOCOR_20A_MP_W22.04.6_P5`).
הקונטיינר כולל 29 מחיצות שונות, הכוללות מספר מעבדים שונים (ARM Cortex-A7, ARM Cortex-M4, CEVA DSP) וקובצי הגדרות (NVRAM, MMI Resources, APN).

Ghidra אינה מסוגלת לנתח קובץ PAC ישירות כמקשה אחת ללא פירוק ומיפוי כתובות הזיכרון (Load Addresses).

---

## 2. מפת מחיצות ורכיבי הקושחה שחולצו

| מחיצה | קובץ בינארי | גודל (בתים) | ארכיטקטורה | כתובת טעינה (Base Address) | תפקיד |
|---|---|---|---|---|---|
| **BOOT0** | `boot0.bin` | 31,684 | `ARM:LE:32:v7` | `0x00006200` (קוד: `0x00006400`) | Primary Bootloader (SPL) – אימות חתימות, anti-rollback וטעינת boot1 |
| **BOOT1** | `boot1.bin` | 154,948 | `ARM:LE:32:v7` | `0x80100000` (קוד: `0x80100200`) | Secondary Bootloader – אתחול מסך, דרייבר פלאש (FTL), טעינת Kernel ו-User |
| **FDL1** | `fdl1.bin` | 32,596 | `ARM:LE:32:v7` | `0x00006200` (קוד: `0x00006400`) | Flash Download Loader שלב 1 (פרוטוקול USB, אתחול DDR) |
| **FDL2** | `fdl2.bin` | 63,972 | `ARM:LE:32:v7` | `0x80100000` (קוד: `0x80100200`) | Flash Download Loader שלב 2 (צריבת מחיצות NAND וקריאת דאמפים) |
| **KernelImg** | `EXEC_KERNEL_IMAGE.bin` | 12,947,844 | `ARM:LE:32:v7` | `0x80000000` (כניסה: `0x80a061f4`) | MOCOR RTOS Kernel (תזמון, משימות, דרייברים לחומרה) |
| **UserImg** | `EXEC_USER_IMAGE.bin` | 12,230,884 | `ARM:LE:32:v7` | `0x80000000` (Thumb-2) | אפליקציות, ממשק MMI, מחסנית HTTP/WAP ו-mbedTLS 2.6 |
| **CM4CODE** | `PM_nemol_cm4.bin` | 55,500 | `ARM:LE:32:Cortex` | Raw Cortex-M4 | קושחת ניהול צריכת חשמל (Power Management) |
| **LTEDSPCODE** | `T117_CAT1_LTEA_DSP.bin` | 3,145,728 | CEVA DSP | DSP Core | מודם LTE/CAT-1 |
| **GSMDSPCODE** | `NEMOL_CAT1_EVS_DM_DSP.bin`| 2,654,208 | CEVA DSP | DSP Core | מודם GSM/EVS |
| **MMIRes** | `mmi_res_240X320_QB.bin` | 18,605,584 | Data (Images/Fonts) | N/A | גרפיקה, גופנים ומחרוזות תרגום (עברית/אנגלית ב-UCS-2LE) |
| **NV** | `...nvitem...bin` | 723,880 | Data (NVRAM) | N/A | רשומות כיול ותפריט ראשי (רשומה `0x02A8`) |

---

## 3. מבנה הכותרות (DHTB) ומנגנון החתימה (RSA-2048)

כל אחד מקובצי ההפעלה של ה-Cortex-A7 (`boot0`, `boot1`, `fdl1`, `fdl2`, `EXEC_KERNEL_IMAGE`, `EXEC_USER_IMAGE`) עטוף במבנה קבוע:
1. **כותרת DHTB (512 בתים):**
   - מתחילה ב-Magic `DHTB` (`44 48 54 42 01 00 00 00`).
   - ב-Offset `0x30` (`48`): שדה `uint32_le` שמגדיר את אורך הפיילוד המדויק.
2. **פיילוד הקוד הנקי (Raw Code Payload):**
   - מתחיל ב-Offset `512` בדיוק.
   - מכיל וקטורי אתחול של ARM (`ldr pc, [pc, #...]`).
3. **טריילר קריפטוגרפי (692 בתים בדיוק):**
   - מכיל את ה-Hash (SHA-256) של הפיילוד.
   - שרשרת תעודות מפתחות ציבוריים (Certificate Chain).
   - חתימת RSA-2048 באורך 256 בתים בסוף הקובץ.

---

## 4. הקמת פרויקט ה-Ghidra וביצוע הניתוח האוטומטי

### א. עקיפת מגבלת ה-Unicode ב-Java/Windows
בגלל ששם התיקייה כולל תווים בעברית (`פרוייקטים\נוקיה`), מנתח ה-URI וה-XML של Java (Xerces) נכשל בטעינת קטלוגים.
הבעיה נפתרה על ידי מיפוי כונן וירטואלי נקי:
```powershell
subst N: "c:\Users\Eli\OneDrive - PCMASTER\Desktop\פרוייקטים\נוקיה"
```

### ב. חילוץ הקוד הנקי (Stripped Raw Payloads)
נבנו קבצים נקיים בתיקיית `ghidra_inputs/` (ללא כותרת DHTB וללא טריילר חתימת RSA) כדי ש-Ghidra תמפה את האופסטים ישירות לפקודות המכונה.

### ג. ניתוח ב-Ghidra Headless Analyzer
נוצר פרויקט Ghidra רשמי:
📁 **נתיב הפרויקט**: `N:\ghidra\projects\Nokia3210.gpr` (`Nokia3210.rep`)

הרכיבים הבאים יובאו ונותחו במלואם עם Decompiler, פיענוח מחרוזות, Switch Analysis וזיהוי פונקציות:
1. **`boot0_raw.bin`** (`ARM:LE:32:v7` ב-`0x00006400`):
   - סך הכל **164 פונקציות** זוהו ופוענחו.
   - זוהו שגרות אימות החתימה (`verify`, `antiroll_back`, `get_sechdr_Addr`).
2. **`boot1_raw.bin`** (`ARM:LE:32:v7` ב-`0x80100200`):
   - סך הכל **541 פונקציות** זוהו ופוענחו.
   - זוהו שגרות טעינת הפלאש (`SCI_FTL_Load`), שגרות אימות ה-Kernel (`verify kernel suc: %x`, `run kernel:%x`) ומיפוי מחיצות ה-OSA/OSB.
3. **`fdl1_raw.bin`** (`ARM:LE:32:v7` ב-`0x00006400`):
   - פוענח מנגנון הלחיצה/Boot Handshake ופרוטוקול ה-USB להורדה.
4. **`fdl2_raw.bin`** (`ARM:LE:32:v7` ב-`0x80100200`):
   - פוענח פרוטוקול הפקודות המלא מול כלי ה-SPD Research Tool.
5. **`EXEC_KERNEL_IMAGE_raw.bin`** (12.9MB) ו-**`EXEC_USER_IMAGE_raw.bin`** (12.2MB):
   - יובאו לפרויקט ה-Ghidra בכתובת הבסיס `0x80000000`. הם זמינים לחלוטין לצפייה ודיקומפילציה נקודתית בממשק הגרפי.

---

## 5. פתיחה בממשק הגרפי של Ghidra (GUI)

כדי לפתוח את הפרויקט ולחקור את הפונקציות:
1. ודא שהכונן `N:` ממופה (או הרץ `subst N: "$pwd"`).
2. הרץ את Ghidra:
   ```cmd
   N:\ghidra\ghidra_12.1_PUBLIC_20260513\ghidra_12.1_PUBLIC\ghidraRun.bat
   ```
3. בחר ב-**File -> Open Project** ובחר ב:
   `N:\ghidra\projects\Nokia3210.gpr`
4. יוצגו כל 6 הקבצים הבינאריים עם כל הפונקציות, המשתנים והפיענוחים המוכנים.
