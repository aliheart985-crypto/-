"""
test_comprehensive.py
اختبار شامل لمنصة "مدرستي العراق" — يغطي كل الميزات الأساسية + الجديدة.

طريقة التشغيل:
    python3 test_comprehensive.py
يطلب: Admin email ثم Admin password (نفس حساب السوبر أدمن).

كل خطوة مستقلة (try/except) — فشل خطوة وحدة ما يوقف باقي الاختبار.
بالنهاية يطبع ملخص PASS/FAIL لكل شي.
"""

import requests
import getpass
import uuid
import datetime

SUPABASE_URL = "https://awzcxkqtpllrxqmkiylr.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_JeCyZm3nZ4fRUUR1WEqeLQ_kz-qg8jJ"
AUTH_URL = SUPABASE_URL + "/auth/v1"
REST_URL = SUPABASE_URL + "/rest/v1"

BASE_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Content-Type": "application/json",
}

results = []
created = {}  # نخزن هنا كل شي ننشئه لحذفه بالنهاية (تنظيف)


def log(step, ok, detail=""):
    results.append((step, "PASS" if ok else "FAIL", detail))
    print(("✅ " if ok else "❌ ") + step + (f" -- {detail}" if detail and not ok else ""))


def auth_headers(token):
    return {**BASE_HEADERS, "Authorization": f"Bearer {token}"}


def signup(email, password, full_name, role, extra_meta=None):
    """يسجل حساب جديد بـ Supabase Auth، يرجع (ok, user_id_or_error)"""
    payload = {"email": email, "password": password, "data": {"full_name": full_name, "role": role}}
    if extra_meta:
        payload["data"].update(extra_meta)
    r = requests.post(f"{AUTH_URL}/signup", headers=BASE_HEADERS, json=payload)
    if r.status_code < 400:
        j = r.json()
        return True, j.get("user", {}).get("id") or j.get("id")
    return False, r.text


def login(email, password):
    r = requests.post(f"{AUTH_URL}/token?grant_type=password", headers=BASE_HEADERS,
                       json={"email": email, "password": password})
    if r.status_code < 400:
        j = r.json()
        return j.get("access_token"), j.get("user", {}).get("id")
    return None, None


def main():
    print("=== اختبار شامل — مدرستي العراق ===\n")
    admin_email = input("Admin email: ").strip()
    admin_password = getpass.getpass("Admin password: ")

    admin_token, admin_uid = login(admin_email, admin_password)
    log("تسجيل دخول الأدمن", admin_token is not None)
    if not admin_token:
        print("توقف الاختبار — تعذر تسجيل دخول الأدمن.")
        print_summary()
        return
    admin_headers = auth_headers(admin_token)

    # جلب school_id تبع الأدمن
    school_id = None
    try:
        r = requests.get(f"{REST_URL}/users?id=eq.{admin_uid}&select=school_id,role", headers=admin_headers)
        rows = r.json()
        if rows:
            school_id = rows[0].get("school_id")
        log("جلب school_id للأدمن", school_id is not None, str(rows))
    except Exception as e:
        log("جلب school_id للأدمن", False, str(e))

    unique = uuid.uuid4().hex[:6]

    # ---------------------------------------------------------------
    print("\n--- 1) اختبار أمان التسجيل (رمز خطأ ما ينشئ حساب) ---")
    fake_email = f"test_wrongcode_{unique}@example.com"
    ok, res = signup(fake_email, "Test1234!", "طالب اختبار رمز خطأ", "student", {"verify_code": "000000-invalid"})
    # نحاول تسجيل نفس الايميل مرة ثانية؛ لو الحساب انحذف/ما انبنى، ما لازم تطلع "User already registered"
    ok2, res2 = signup(fake_email, "Test1234!", "طالب اختبار رمز خطأ", "student", {"verify_code": "000000-invalid"})
    already_registered = isinstance(res2, str) and "already registered" in res2.lower()
    log("رمز التحقق الخاطئ ما يسبب قفل الإيميل (already registered)", not already_registered,
        res2 if already_registered else "")

    # ---------------------------------------------------------------
    print("\n--- 2) تسجيل معلم اختباري ---")
    teacher_email = f"test_teacher_{unique}@example.com"
    ok, teacher_uid = signup(teacher_email, "Test1234!", "معلم اختباري", "teacher")
    log("تسجيل معلم جديد", ok, str(teacher_uid) if not ok else "")
    if ok:
        created["teacher_uid"] = teacher_uid
        created["teacher_email"] = teacher_email

    # موافقة الأدمن على المعلم (تفعيل الحساب)
    if created.get("teacher_uid"):
        try:
            r = requests.patch(f"{REST_URL}/users?id=eq.{created['teacher_uid']}", headers=admin_headers,
                                json={"status": "approved", "school_id": school_id})
            log("موافقة الأدمن على المعلم", r.status_code < 400, r.text if r.status_code >= 400 else "")
        except Exception as e:
            log("موافقة الأدمن على المعلم", False, str(e))

    teacher_token, _ = login(teacher_email, "Test1234!") if created.get("teacher_uid") else (None, None)
    log("تسجيل دخول المعلم بعد الموافقة", teacher_token is not None)

    # ---------------------------------------------------------------
    print("\n--- 3) إنشاء صف اختباري ---")
    class_id = None
    try:
        r = requests.post(f"{REST_URL}/classes", headers={**admin_headers, "Prefer": "return=representation"},
                           json={"school_id": school_id, "grade_level": "اختبار", "section_name": "ص"})
        if r.status_code < 400:
            class_id = r.json()[0]["id"]
            created["class_id"] = class_id
        log("إنشاء صف اختباري", r.status_code < 400, r.text if r.status_code >= 400 else "")
    except Exception as e:
        log("إنشاء صف اختباري", False, str(e))

    # ---------------------------------------------------------------
    print("\n--- 4) تسجيل طالب اختباري (رمز صحيح) ---")
    student_verify_code = "TST" + unique
    student_record_id = None
    try:
        r = requests.post(f"{REST_URL}/students", headers={**admin_headers, "Prefer": "return=representation"},
                           json={"school_id": school_id, "full_name": "طالب اختبار شامل",
                                  "class_id": class_id, "verify_code": student_verify_code, "status": "active"})
        if r.status_code < 400:
            student_record_id = r.json()[0]["id"]
            created["student_record_id"] = student_record_id
        log("إنشاء سجل طالب بقاعدة البيانات", r.status_code < 400, r.text if r.status_code >= 400 else "")
    except Exception as e:
        log("إنشاء سجل طالب بقاعدة البيانات", False, str(e))

    student_email = f"test_student_{unique}@example.com"
    student_uid = None
    if student_record_id:
        ok, student_uid = signup(student_email, "Test1234!", "طالب اختبار شامل", "student",
                                  {"verify_code": student_verify_code, "student_record_id": student_record_id})
        log("تسجيل حساب الطالب بالرمز الصحيح", ok, str(student_uid) if not ok else "")
        if ok:
            created["student_uid"] = student_uid
            created["student_email"] = student_email

    # ---------------------------------------------------------------
    print("\n--- 5) تسجيل ولي أمر اختباري (رمز صحيح) وربطه ---")
    parent_email = f"test_parent_{unique}@example.com"
    ok, parent_uid = signup(parent_email, "Test1234!", "ولي أمر اختباري", "parent")
    log("تسجيل حساب ولي الأمر", ok, str(parent_uid) if not ok else "")
    if ok:
        created["parent_uid"] = parent_uid
        created["parent_email"] = parent_email
        try:
            r = requests.patch(f"{REST_URL}/users?id=eq.{parent_uid}", headers=admin_headers,
                                json={"status": "approved"})
            log("موافقة الأدمن على ولي الأمر", r.status_code < 400, r.text if r.status_code >= 400 else "")
        except Exception as e:
            log("موافقة الأدمن على ولي الأمر", False, str(e))

        if student_record_id:
            try:
                r = requests.post(f"{REST_URL}/parent_student", headers=admin_headers,
                                   json={"parent_id": parent_uid, "student_id": student_record_id})
                log("ربط ولي الأمر بالطالب", r.status_code < 400, r.text if r.status_code >= 400 else "")
            except Exception as e:
                log("ربط ولي الأمر بالطالب", False, str(e))

    # ---------------------------------------------------------------
    print("\n--- 6) رصد درجة + التحقق من إشعار تلقائي لولي الأمر ---")
    if student_record_id:
        try:
            r = requests.post(f"{REST_URL}/grades", headers={**admin_headers, "Prefer": "return=representation"},
                               json={"student_id": student_record_id, "subject": "اختبار", "grade_value": 95,
                                     "school_id": school_id})
            log("رصد درجة للطالب", r.status_code < 400, r.text if r.status_code >= 400 else "")
        except Exception as e:
            log("رصد درجة للطالب", False, str(e))

    if parent_uid:
        try:
            r = requests.get(f"{REST_URL}/notifications?receiver_id=eq.{parent_uid}&order=created_at.desc&limit=1",
                              headers=admin_headers)
            got_notif = r.status_code < 400 and len(r.json()) > 0
            log("وصول إشعار تلقائي لولي الأمر عن الدرجة", got_notif, r.text if not got_notif else "")
        except Exception as e:
            log("وصول إشعار تلقائي لولي الأمر عن الدرجة", False, str(e))

    # ---------------------------------------------------------------
    print("\n--- 7) نظام الاشتراك بالإيميل (ميزة اليوم) ---")
    if parent_uid:
        tomorrow = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        try:
            r = requests.post(f"{REST_URL}/notification_preferences?on_conflict=user_id",
                               headers={**admin_headers, "Prefer": "resolution=merge-duplicates"},
                               json={"user_id": parent_uid, "email_enabled": True,
                                     "email_subscription_active": True, "email_subscription_expires_at": tomorrow})
            log("تفعيل اشتراك الإيميل لولي الأمر", r.status_code < 400, r.text if r.status_code >= 400 else "")
        except Exception as e:
            log("تفعيل اشتراك الإيميل لولي الأمر", False, str(e))

        try:
            r = requests.get(f"{REST_URL}/notification_preferences?user_id=eq.{parent_uid}"
                              f"&select=email_subscription_active,email_subscription_expires_at", headers=admin_headers)
            rows = r.json()
            active_ok = r.status_code < 400 and rows and rows[0].get("email_subscription_active") is True
            log("التحقق من قراءة حالة الاشتراك (فعّال)", active_ok, str(rows) if not active_ok else "")
        except Exception as e:
            log("التحقق من قراءة حالة الاشتراك (فعّال)", False, str(e))

        try:
            r = requests.patch(f"{REST_URL}/notification_preferences?user_id=eq.{parent_uid}",
                                headers=admin_headers, json={"email_subscription_active": False})
            log("إلغاء اشتراك الإيميل لولي الأمر", r.status_code < 400, r.text if r.status_code >= 400 else "")
        except Exception as e:
            log("إلغاء اشتراك الإيميل لولي الأمر", False, str(e))

    # ---------------------------------------------------------------
    print("\n--- 8) تعيين شعبة للطالب (اختبار صفحة الطلاب المبسّطة) ---")
    if student_record_id and class_id:
        try:
            r = requests.patch(f"{REST_URL}/students?id=eq.{student_record_id}", headers=admin_headers,
                                json={"class_id": class_id})
            log("تعيين شعبة للطالب", r.status_code < 400, r.text if r.status_code >= 400 else "")
        except Exception as e:
            log("تعيين شعبة للطالب", False, str(e))

    # ---------------------------------------------------------------
    print("\n--- 9) تنظيف: حذف كل البيانات التجريبية ---")
    cleanup(admin_headers)

    print_summary()


def cleanup(admin_headers):
    try:
        if created.get("student_record_id"):
            requests.post(f"{REST_URL}/rpc/delete_student_safe", headers=admin_headers,
                          json={"p_student_id": created["student_record_id"]})
        if created.get("class_id"):
            requests.delete(f"{REST_URL}/classes?id=eq.{created['class_id']}", headers=admin_headers)
        log("تنظيف البيانات التجريبية (محاولة)", True,
            "ملاحظة: حسابات auth.users (معلم/طالب/ولي أمر) ما تنحذف تلقائيًا — احذفها يدويًا من Supabase → Authentication لو تحب")
    except Exception as e:
        log("تنظيف البيانات التجريبية (محاولة)", False, str(e))


def print_summary():
    print("\n===== الملخص النهائي =====")
    passed = sum(1 for _, s, _ in results if s == "PASS")
    total = len(results)
    for step, status, detail in results:
        print(f"{status}: {step}" + (f"  ({detail})" if detail and status == "FAIL" else ""))
    print(f"\n{passed}/{total} PASS")


if __name__ == "__main__":
    main()
