"""
fix_passwords.py  —  Resets demo passwords to plain text in MySQL.
Usage:  py fix_passwords.py
"""

print("=" * 60)
print("  CollegeBoard — Password Reset (Plain Text)")
print("=" * 60)

try:
    import MySQLdb

    HOST     = 'localhost'
    USER     = 'root'
    PASSWORD = input("Enter your MySQL root password: ").strip()
    DB       = 'college_noticeboard'

    conn = MySQLdb.connect(host=HOST, user=USER, passwd=PASSWORD, db=DB)
    cur  = conn.cursor()

    cur.execute("UPDATE users SET password='Admin@123'   WHERE email='admin@college.edu'")
    cur.execute("UPDATE users SET password='Faculty@123' WHERE email='faculty@college.edu'")
    cur.execute("UPDATE users SET password='Student@123' WHERE email='student@college.edu'")
    conn.commit()

    cur.execute("SELECT id, full_name, email, role, password, is_active FROM users")
    users = cur.fetchall()

    print(f"\n✅ Done! All passwords updated.\n")
    print(f"{'ID':<5} {'Name':<22} {'Email':<28} {'Role':<10} {'Password':<15} Active")
    print("-" * 90)
    for u in users:
        print(f"{u[0]:<5} {u[1]:<22} {u[2]:<28} {u[3]:<10} {u[4]:<15} {'Yes' if u[5] else 'No'}")

    cur.close()
    conn.close()

    print("\nLogin credentials:")
    print("  Admin   → admin@college.edu    / Admin@123")
    print("  Faculty → faculty@college.edu  / Faculty@123")
    print("  Student → student@college.edu  / Student@123")
    print("\nNow run:  py app.py")

except Exception as e:
    print(f"\n❌ Error: {e}")
