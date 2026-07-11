"""
test_comprehensive.py (v2 — مطابق لكود التطبيق الحقيقي بالضبط)
اختبار شامل لمنصة "مدرستي العراق".

طريقة التشغيل:
    python3 test_comprehensive.py
يطلب: Admin email ثم Admin password.
"""

import requests
import getpass
import uuid
import datetime

SUPABASE_URL = "https://awzcxkqtpllrxqmkiylr.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_JeCyZm3nZ4fRUUR1WEqeLQ_kz-qg8jJ"
AUTH_URL = SUPABASE_URL + "/auth/v1"
REST_URL = SUPABASE_URL + "/rest/v1"

BASE_HEADERS = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}

results = []
created = {}


def log(step, ok, detail=""):
    results.append((step, "PASS" if ok else "FAIL", detail))
    print(("✅ " if ok else "❌ ") + step + (f" -- {detail}" if detail and not ok else ""))


def auth_headers(token):
    return {**BASE_HEADERS, "Authorization": f"Bearer {token}"}


def signup_and_create_profile(email, password, full_name, role, school_id):
    """يطابق بالضبط منطق التطبيق الحقيقي: auth.signup ثم إنشاء صف public.users."""
    r = requests.post(f"{AUTH_URL}/signup", headers=BASE_HEADERS,
                       json={"email": email, "password": password})
    if r.status_code >= 400:
        return False, None, None, r.text
    data = r.json()
    user_id = data.get("user", {}).get("id") if data.get("user") else data.get("id")
    access_token = data.get("access_token")
    r2 = requests.post(f"{REST_URL}/users",
                        headers={**auth_headers(access_token or SUPABASE_ANON_KEY), "Prefer": "return=representation"},
                        json={"id": user_id, "full_name": full_name, "role": role, "status": "pending", "school_id": school_id})
    if r2.status_code >= 400:
        return False, user_id, access_token, r2.text
    return True, user_id, access_token, ""


def login(email, password):
    r = requests.post(f"{AUTH_URL}/token?grant_type=password", headers=BASE_HEADERS,
                       json={"email": email, "password": password})
    if r.status_code < 400:
        j = r.json()
        return j.get("access_token"), j.get("user", {}).get("id")
    return None, None


def main():
    print("=== اختبار شامل — مدرستي العراق (v2) ===\n")
    admin_email = input("Admin email: ").strip()
    admin_password = getpass.getpass("Admin password: ")

    admin_token, admin_uid = login(admin_email, admin_password)
    log("تسجيل دخول الأدمن", admin_token is not None)
    if not admin_token:
        print_summary(); return
    admin_headers = auth_headers(admin_token)

    school_id = None
    try:
        r = requests.get(f"{REST_URL}/users?id=eq.{admin_uid}&select=school_id", headers=admin_headers)
        rows = r.json()
        school_id = rows[0].get("school_id") if rows else None
        log("جلب school_id للأدمن", school_id is not None, str(rows))
    except Exception as e:
        log("جلب school_id للأدمن", False, str(e))

    unique = uuid.uuid4().hex[:6]

    print("\n--- 1) تجهيز مرحلة دراسية وصف اختباري ---")
    stage_id = None
    try:
        r = requests.get(f"{REST_URL}/education_stages?school_id=eq.{school_id}&select=id&limit=1", headers=admin_headers)
        rows = r.json()
        if rows:
            stage_id = rows[0]["id"]
        else:
            r2 = requests.post(f"{REST_URL}/education_stages", headers={**admin_headers, "Prefer": "return=representation"},
                                json={"school_id": school_id, "name": "مرحلة اختبار"})
            if r2.status_code < 400:
                stage_id = r2.json()[0]["id"]
                created["stage_id"] = stage_id
        log("تجهيز مرحلة دراسية", stage_id is not None)
    except Exception as e:
        log("تجهيز مرحلة دراسية", False, str(e))

    class_id = None
    try:
        r = requests.post(f"{REST_URL}/classes", headers={**admin_headers, "Prefer": "return=representation"},
                           json={"school_id": school_id, "stage_id": stage_id, "grade_level": "اختبار",
                                 "section_name": "شعبة", "name": "اختبار شعبة " + unique})
        if r.status_code < 400:
            class_id = r.json()[0]["id"]
            created["class_id"] = class_id
        log("إنشاء صف اختباري", r.status_code < 400, r.text if r.status_code >= 400 else "")
    except Exception as e:
        log("إنشاء صف اختباري", False, str(e))

    print("\n--- 2) إنشاء سجل طالب (من الأدمن) ---")
    student_verify_code = "TST" + unique
    student_record_id = None
    try:
        r = requests.post(f"{REST_URL}/students", headers={**admin_headers, "Prefer": "return=representation"},
                           json={"school_id": school_id, "full_name": "طالب اختبار شامل " + unique,
                                 "verify_code": student_verify_code, "class_id": class_id})
        if r.status_code < 400:
            student_record_id = r.json()[0]["id"]
            created["student_record_id"] = student_record_id
        log("إنشاء سجل طالب", r.status_code < 400, r.text if r.status_code >= 400 else "")
    except Exception as e:
        log("إنشاء سجل طالب", False, str(e))

    print("\n--- 3) اختبار أمان رمز التحقق (verify_student_code) ---")
    if student_record_id:
        try:
            r = requests.post(f"{REST_URL}/rpc/verify_student_code", headers=BASE_HEADERS,
                               json={"p_student_id": student_record_id, "p_code": "رمز-خطأ-تمامًا"})
            is_valid_wrong = r.json() if r.status_code < 400 else None
            log("رمز خاطئ يرجع false (مو يسمح بالتسجيل)", is_valid_wrong is False, str(r.text))
        except Exception as e:
            log("رمز خاطئ يرجع false (مو يسمح بالتسجيل)", False, str(e))

        try:
            r = requests.post(f"{REST_URL}/rpc/verify_student_code", headers=BASE_HEADERS,
                               json={"p_student_id": student_record_id, "p_code": student_verify_code})
            is_valid_correct = r.json() if r.status_code < 400 else None
            log("رمز صحيح يرجع true", is_valid_correct is True, str(r.text))
        except Exception as e:
            log("رمز صحيح يرجع true", False, str(e))

    print("\n--- 4) تسجيل معلم اختباري كامل ---")
    teacher_email = f"test_teacher_{unique}@example.com"
    ok, teacher_uid, _, err = signup_and_create_profile(teacher_email, "Test1234!", "معلم اختباري", "teacher", school_id)
    log("تسجيل معلم (auth + profile)", ok, err)
    if ok:
        created["teacher_uid"] = teacher_uid
        try:
            r = requests.patch(f"{REST_URL}/users?id=eq.{teacher_uid}", headers=admin_headers, json={"status": "approved"})
            log("موافقة الأدمن على المعلم", r.status_code < 400)
        except Exception as e:
            log("موافقة الأدمن على المعلم", False, str(e))
        t_token, _ = login(teacher_email, "Test1234!")
        log("دخول المعلم بعد الموافقة", t_token is not None)

    print("\n--- 5) تسجيل حساب الطالب (بالرمز الصحيح) وربطه ---")
    student_email = f"test_student_{unique}@example.com"
    ok, student_uid, _, err = signup_and_create_profile(student_email, "Test1234!", "طالب اختبار شامل", "student", school_id)
    log("تسجيل حساب طالب (auth + profile)", ok, err)
    if ok and student_record_id:
        created["student_uid"] = student_uid
        try:
            r = requests.post(f"{REST_URL}/rpc/link_student_self", headers=BASE_HEADERS,
                               json={"p_student_id": student_record_id, "p_user_id": student_uid})
            log("ربط حساب الطالب بسجله (link_student_self)", r.status_code < 400, r.text if r.status_code >= 400 else "")
        except Exception as e:
            log("ربط حساب الطالب بسجله (link_student_self)", False, str(e))
        try:
            r = requests.patch(f"{REST_URL}/users?id=eq.{student_uid}", headers=admin_headers, json={"status": "approved"})
            log("موافقة الأدمن على الطالب", r.status_code < 400)
        except Exception as e:
            log("موافقة الأدمن على الطالب", False, str(e))

    print("\n--- 6) تسجيل ولي أمر (بالرمز الصحيح) وربطه ---")
    parent_email = f"test_parent_{unique}@example.com"
    ok, parent_uid, parent_token, err = signup_and_create_profile(parent_email, "Test1234!", "ولي أمر اختباري", "parent", school_id)
    log("تسجيل حساب ولي أمر (auth + profile)", ok, err)
    if ok:
        created["parent_uid"] = parent_uid
        if student_record_id:
            try:
                r = requests.post(f"{REST_URL}/rpc/verify_child_code", headers=BASE_HEADERS,
                                   json={"p_child_id": student_record_id, "p_code": student_verify_code})
                is_valid = r.json() if r.status_code < 400 else None
                log("verify_child_code يتحقق من رمز الطالب لولي الأمر", is_valid is True, str(r.text))
            except Exception as e:
                log("verify_child_code يتحقق من رمز الطالب لولي الأمر", False, str(e))
            try:
                r = requests.post(f"{REST_URL}/parent_student",
                                   headers={**auth_headers(parent_token), "Prefer": "return=representation"},
                                   json={"parent_id": parent_uid, "student_id": student_record_id})
                log("ربط ولي الأمر بالطالب", r.status_code < 400, r.text if r.status_code >= 400 else "")
            except Exception as e:
                log("ربط ولي الأمر بالطالب", False, str(e))
        try:
            r = requests.patch(f"{REST_URL}/users?id=eq.{parent_uid}", headers=admin_headers, json={"status": "approved"})
            log("موافقة الأدمن على ولي الأمر", r.status_code < 400)
        except Exception as e:
            log("موافقة الأدمن على ولي الأمر", False, str(e))

    print("\n--- 7) رصد درجة + التحقق من إشعار تلقائي لولي الأمر ---")
    subject_id = None
    if student_record_id:
        try:
            r = requests.get(f"{REST_URL}/subjects?school_id=eq.{school_id}&select=id&limit=1", headers=admin_headers)
            subs = r.json()
            if subs:
                subject_id = subs[0]["id"]
            else:
                r2 = requests.post(f"{REST_URL}/subjects", headers={**admin_headers, "Prefer": "return=representation"},
                                    json={"school_id": school_id, "name": "مادة اختبار"})
                if r2.status_code < 400:
                    subject_id = r2.json()[0]["id"]
                    created["subject_id"] = subject_id
            log("تجهيز مادة دراسية", subject_id is not None)
        except Exception as e:
            log("تجهيز مادة دراسية", False, str(e))

        if subject_id:
            try:
                r = requests.post(f"{REST_URL}/grades", headers={**admin_headers, "Prefer": "return=representation"},
                                   json={"school_id": school_id, "student_id": student_record_id, "subject_id": subject_id,
                                         "exam_type": "اختبار", "score": 95, "max_score": 100})
                log("رصد درجة للطالب", r.status_code < 400, r.text if r.status_code >= 400 else "")
            except Exception as e:
                log("رصد درجة للطالب", False, str(e))

    if created.get("parent_uid"):
        try:
            r = requests.get(f"{REST_URL}/notifications?receiver_id=eq.{created['parent_uid']}&order=created_at.desc&limit=1",
                              headers=admin_headers)
            got = r.status_code < 400 and len(r.json()) > 0
            log("وصول إشعار تلقائي لولي الأمر عن الدرجة", got, r.text if not got else "")
        except Exception as e:
            log("وصول إشعار تلقائي لولي الأمر عن الدرجة", False, str(e))

    if created.get("student_uid"):
        try:
            r = requests.get(f"{REST_URL}/notifications?receiver_id=eq.{created['student_uid']}&order=created_at.desc&limit=1",
                              headers=admin_headers)
            got = r.status_code < 400 and len(r.json()) > 0
            log("وصول إشعار تلقائي للطالب نفسه عن الدرجة (ميزة جديدة)", got, r.text if not got else "")
        except Exception as e:
            log("وصول إشعار تلقائي للطالب نفسه عن الدرجة (ميزة جديدة)", False, str(e))

    print("\n--- 7ب) بيانات كشف درجات الشعبة (نفس استعلام الجدول الجديد) ---")
    if class_id:
        try:
            r = requests.get(f"{REST_URL}/students?class_id=eq.{class_id}&select=id,full_name,enrollment_number", headers=admin_headers)
            class_students = r.json()
            student_ids_csv = ",".join(s["id"] for s in class_students) if class_students else ""
            r2 = requests.get(f"{REST_URL}/grades?student_id=in.({student_ids_csv})&select=student_id,score,max_score,subjects(name)",
                               headers=admin_headers)
            report_ok = r.status_code < 400 and r2.status_code < 400 and len(class_students) > 0
            log("جلب بيانات كشف درجات الشعبة (طلاب + درجات مع اسم المادة)", report_ok,
                r2.text if r2.status_code >= 400 else "")
        except Exception as e:
            log("جلب بيانات كشف درجات الشعبة (طلاب + درجات مع اسم المادة)", False, str(e))

    print("\n--- 8) نظام الاشتراك بالإيميل (ميزة اليوم) ---")
    if created.get("parent_uid"):
        parent_uid = created["parent_uid"]
        expiry = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        try:
            r = requests.post(f"{REST_URL}/notification_preferences?on_conflict=user_id",
                               headers={**admin_headers, "Prefer": "resolution=merge-duplicates"},
                               json={"user_id": parent_uid, "email_enabled": True,
                                     "email_subscription_active": True, "email_subscription_expires_at": expiry})
            log("تفعيل اشتراك الإيميل لولي الأمر", r.status_code < 400, r.text if r.status_code >= 400 else "")
        except Exception as e:
            log("تفعيل اشتراك الإيميل لولي الأمر", False, str(e))
        try:
            r = requests.get(f"{REST_URL}/notification_preferences?user_id=eq.{parent_uid}"
                              f"&select=email_subscription_active,email_subscription_expires_at", headers=admin_headers)
            rows = r.json()
            ok_active = r.status_code < 400 and rows and rows[0].get("email_subscription_active") is True
            log("قراءة حالة الاشتراك (فعّال)", ok_active, str(rows) if not ok_active else "")
        except Exception as e:
            log("قراءة حالة الاشتراك (فعّال)", False, str(e))
        try:
            r = requests.patch(f"{REST_URL}/notification_preferences?user_id=eq.{parent_uid}",
                                headers=admin_headers, json={"email_subscription_active": False})
            log("إلغاء اشتراك الإيميل", r.status_code < 400, r.text if r.status_code >= 400 else "")
        except Exception as e:
            log("إلغاء اشتراك الإيميل", False, str(e))

    print("\n--- 9) تعيين شعبة للطالب (صفحة الطلاب المبسّطة) ---")
    if student_record_id and class_id:
        try:
            r = requests.patch(f"{REST_URL}/students?id=eq.{student_record_id}", headers=admin_headers, json={"class_id": class_id})
            log("تعيين شعبة للطالب", r.status_code < 400, r.text if r.status_code >= 400 else "")
        except Exception as e:
            log("تعيين شعبة للطالب", False, str(e))

    print("\n--- 10) تنظيف البيانات التجريبية ---")
    try:
        if created.get("student_record_id"):
            requests.post(f"{REST_URL}/rpc/delete_student_safe", headers=admin_headers,
                          json={"p_student_id": created["student_record_id"]})
        if created.get("class_id"):
            requests.delete(f"{REST_URL}/classes?id=eq.{created['class_id']}", headers=admin_headers)
        log("تنظيف البيانات (محاولة)", True,
            "ملاحظة: حسابات auth (معلم/طالب/ولي أمر) تحتاج حذف يدوي من Authentication لو تحب")
    except Exception as e:
        log("تنظيف البيانات (محاولة)", False, str(e))

    print_summary()


def print_summary():
    print("\n===== الملخص النهائي =====")
    passed = sum(1 for _, s, _ in results if s == "PASS")
    total = len(results)
    for step, status, detail in results:
        print(f"{status}: {step}" + (f"  ({detail})" if detail and status == "FAIL" else ""))
    print(f"\n{passed}/{total} PASS")


if __name__ == "__main__":
    main()
