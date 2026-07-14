"""
seed_demo_data.py
ينشئ بيانات عرض تقديمي واقعية لمنصة "مدرستي العراق":
- 1 حساب إدارة جديد
- 8 حسابات معلمين
- 4 حسابات طلاب (مع سجلات طلاب مرتبطة)

كل الحسابات تُنشأ بحالة "معتمد/approved" مباشرة (بدون انتظار موافقة يدوية).
كلمة المرور لجميع الحسابات: Demo@12345

طريقة التشغيل:
    python3 seed_demo_data.py
يطلب: Admin email (حساب سوبر أدمن أو أدمن حالي) ثم Password.
"""

import requests
import getpass

SUPABASE_URL = "https://awzcxkqtpllrxqmkiylr.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_JeCyZm3nZ4fRUUR1WEqeLQ_kz-qg8jJ"
AUTH_URL = SUPABASE_URL + "/auth/v1"
REST_URL = SUPABASE_URL + "/rest/v1"

BASE_HEADERS = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
DEMO_PASSWORD = "Demo@12345"

NEW_ADMIN_NAME = "أحمد جاسم العزاوي"

TEACHERS = [
    "عمر خالد الجبوري",
    "زينب صادق العبيدي",
    "يوسف كريم الدليمي",
    "نور حسين الطائي",
    "مصطفى عبدالرزاق السامرائي",
    "هدى فاضل الربيعي",
    "حيدر ناجي الموسوي",
    "رغد ثامر الجنابي",
]

STUDENTS = [
    "علي كاظم جواد",
    "مريم سالم ياسين",
    "حسن عبدالله فرحان",
    "زهراء محمد صالح",
]

results = []


def log(step, ok, detail=""):
    results.append((step, "PASS" if ok else "FAIL", detail))
    print(("✅ " if ok else "❌ ") + step + (f" -- {detail}" if detail and not ok else ""))


def auth_headers(token):
    return {**BASE_HEADERS, "Authorization": f"Bearer {token}"}


def login(email, password):
    r = requests.post(f"{AUTH_URL}/token?grant_type=password", headers=BASE_HEADERS,
                       json={"email": email, "password": password})
    if r.status_code < 400:
        j = r.json()
        return j.get("access_token"), j.get("user", {}).get("id")
    return None, None


def signup_and_create_profile(email, password, full_name, role, school_id, extra=None):
    r = requests.post(f"{AUTH_URL}/signup", headers=BASE_HEADERS, json={"email": email, "password": password})
    if r.status_code >= 400:
        return False, None, r.text
    data = r.json()
    user_id = data.get("user", {}).get("id") if data.get("user") else data.get("id")
    access_token = data.get("access_token")
    profile = {"id": user_id, "full_name": full_name, "role": role, "status": "approved", "school_id": school_id}
    if extra:
        profile.update(extra)
    r2 = requests.post(f"{REST_URL}/users",
                        headers={**auth_headers(access_token or SUPABASE_ANON_KEY), "Prefer": "return=representation"},
                        json=profile)
    if r2.status_code >= 400:
        return False, user_id, r2.text
    return True, user_id, ""


def main():
    print("=== توليد بيانات عرض تقديمي — مدرستي العراق ===\n")
    admin_email = input("Admin email (حساب موجود حاليًا): ").strip()
    admin_password = getpass.getpass("Admin password: ")

    admin_token, admin_uid = login(admin_email, admin_password)
    log("تسجيل دخول الأدمن الحالي", admin_token is not None)
    if not admin_token:
        print_summary(); return
    admin_headers = auth_headers(admin_token)

    school_id = None
    try:
        r = requests.get(f"{REST_URL}/users?id=eq.{admin_uid}&select=school_id", headers=admin_headers)
        rows = r.json()
        school_id = rows[0].get("school_id") if rows else None
        log("جلب school_id", school_id is not None, str(rows))
    except Exception as e:
        log("جلب school_id", False, str(e))
    if not school_id:
        print("توقف — ما قدرنا نحدد المدرسة."); print_summary(); return

    # جلب صف موجود (أو إنشاء واحد افتراضي) لتعيين الطلاب عليه
    class_id = None
    try:
        r = requests.get(f"{REST_URL}/classes?school_id=eq.{school_id}&select=id&limit=1", headers=admin_headers)
        rows = r.json()
        if rows:
            class_id = rows[0]["id"]
        log("تحديد صف لتعيين الطلاب", class_id is not None, "سيُنشأ الطلاب بدون شعبة" if not class_id else "")
    except Exception as e:
        log("تحديد صف لتعيين الطلاب", False, str(e))

    print("\n--- 1) حساب الإدارة الجديد ---")
    admin_email_new = "admin.demo@madrasati.app"
    ok, uid, err = signup_and_create_profile(admin_email_new, DEMO_PASSWORD, NEW_ADMIN_NAME, "admin", school_id)
    log(f"إنشاء حساب إدارة: {NEW_ADMIN_NAME} ({admin_email_new})", ok, err)

    print("\n--- 2) حسابات المعلمين (8) ---")
    for i, name in enumerate(TEACHERS, start=1):
        email = f"teacher{i}.demo@madrasati.app"
        ok, uid, err = signup_and_create_profile(email, DEMO_PASSWORD, name, "teacher", school_id)
        log(f"معلم {i}: {name} ({email})", ok, err)

    print("\n--- 3) حسابات الطلاب (4) ---")
    for i, name in enumerate(STUDENTS, start=1):
        verify_code = f"DEMO{i}{i}{i}{i}"
        student_id = None
        try:
            r = requests.post(f"{REST_URL}/students", headers={**admin_headers, "Prefer": "return=representation"},
                               json={"school_id": school_id, "full_name": name, "verify_code": verify_code,
                                     "class_id": class_id, "status": "active"})
            if r.status_code < 400:
                student_id = r.json()[0]["id"]
            log(f"سجل الطالب {i}: {name}", r.status_code < 400, r.text if r.status_code >= 400 else "")
        except Exception as e:
            log(f"سجل الطالب {i}: {name}", False, str(e))

        if student_id:
            email = f"student{i}.demo@madrasati.app"
            ok, user_id, err = signup_and_create_profile(email, DEMO_PASSWORD, name, "student", school_id)
            log(f"حساب الطالب {i}: {name} ({email})", ok, err)
            if ok:
                try:
                    r = requests.post(f"{REST_URL}/rpc/link_student_self", headers=BASE_HEADERS,
                                       json={"p_student_id": student_id, "p_user_id": user_id})
                    log(f"ربط حساب الطالب {i} بسجله", r.status_code < 400, r.text if r.status_code >= 400 else "")
                except Exception as e:
                    log(f"ربط حساب الطالب {i} بسجله", False, str(e))

    print_summary()
    print("\n📋 بيانات الدخول لكل الحسابات الجديدة:")
    print(f"   كلمة المرور الموحّدة: {DEMO_PASSWORD}")
    print(f"   الإدارة: {admin_email_new}")
    for i in range(1, 9):
        print(f"   معلم {i}: teacher{i}.demo@madrasati.app")
    for i in range(1, 5):
        print(f"   طالب {i}: student{i}.demo@madrasati.app")


def print_summary():
    print("\n===== الملخص النهائي =====")
    passed = sum(1 for _, s, _ in results if s == "PASS")
    total = len(results)
    for step, status, detail in results:
        print(f"{status}: {step}" + (f"  ({detail})" if detail and status == "FAIL" else ""))
    print(f"\n{passed}/{total} PASS")


if __name__ == "__main__":
    main()
