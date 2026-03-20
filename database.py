import aiosqlite


DB_PATH = "school_bot.db"


def connect():
    return aiosqlite.connect(DB_PATH)


async def prepare_db(db) -> None:
    db.row_factory = aiosqlite.Row


async def fetch_one(query: str, params: tuple = ()):
    async with connect() as db:
        await prepare_db(db)
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        return row


async def fetch_all(query: str, params: tuple = ()):
    async with connect() as db:
        await prepare_db(db)
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return rows


async def execute(query: str, params: tuple = ()) -> None:
    async with connect() as db:
        await prepare_db(db)
        await db.execute(query, params)
        await db.commit()


async def execute_insert(query: str, params: tuple = ()) -> int:
    async with connect() as db:
        await prepare_db(db)
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.lastrowid


async def init_db() -> None:
    async with connect() as db:
        await prepare_db(db)
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                school_class TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student'
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES users (id)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                grade TEXT,
                teacher_comment TEXT,
                status TEXT NOT NULL DEFAULT 'submitted',
                FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                FOREIGN KEY (student_id) REFERENCES users (id)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS submission_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                position INTEGER NOT NULL,
                FOREIGN KEY (submission_id) REFERENCES submissions (id)
            )
            """
        )
        await db.commit()


async def get_user_by_telegram_id(telegram_id: int):
    return await fetch_one(
        """
        SELECT id, telegram_id, full_name, school_class, role
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )


async def create_user(
    telegram_id: int,
    full_name: str,
    school_class: str,
    role: str = "student",
) -> None:
    await execute(
        """
        INSERT INTO users (telegram_id, full_name, school_class, role)
        VALUES (?, ?, ?, ?)
        """,
        (telegram_id, full_name, school_class, role),
    )


async def get_all_students():
    return await fetch_all(
        """
        SELECT id, telegram_id, full_name, school_class, role
        FROM users
        WHERE role = 'student'
        ORDER BY full_name
        """
    )


async def get_student_by_id(student_id: int):
    return await fetch_one(
        """
        SELECT id, telegram_id, full_name, school_class, role
        FROM users
        WHERE id = ? AND role = 'student'
        """,
        (student_id,),
    )


async def create_assignment(
    student_id: int,
    title: str,
    file_id: str,
    file_type: str,
) -> None:
    await execute(
        """
        INSERT INTO assignments (student_id, title, file_id, file_type)
        VALUES (?, ?, ?, ?)
        """,
        (student_id, title, file_id, file_type),
    )


async def get_student_assignment_number(student_id: int, assignment_id: int):
    result = await fetch_one(
        """
        SELECT COUNT(*) AS assignment_number
        FROM assignments
        WHERE student_id = ? AND id <= ?
        """,
        (student_id, assignment_id),
    )
    return result["assignment_number"] if result else None


async def get_assignments_for_student(student_id: int):
    return await fetch_all(
        """
        SELECT id, student_id, title, file_id, file_type, created_at
        FROM assignments
        WHERE student_id = ?
        ORDER BY id DESC
        """,
        (student_id,),
    )


async def get_assignment_by_id(assignment_id: int):
    return await fetch_one(
        """
        SELECT id, student_id, title, file_id, file_type, created_at
        FROM assignments
        WHERE id = ?
        """,
        (assignment_id,),
    )


async def create_submission(
    assignment_id: int,
    student_id: int,
    file_id: str,
    file_type: str,
) -> int:
    return await execute_insert(
        """
        INSERT INTO submissions (assignment_id, student_id, file_id, file_type)
        VALUES (?, ?, ?, ?)
        """,
        (assignment_id, student_id, file_id, file_type),
    )


async def add_submission_file(
    submission_id: int,
    file_id: str,
    file_type: str,
    position: int,
) -> None:
    await execute(
        """
        INSERT INTO submission_files (submission_id, file_id, file_type, position)
        VALUES (?, ?, ?, ?)
        """,
        (submission_id, file_id, file_type, position),
    )


async def get_submission_files(submission_id: int):
    return await fetch_all(
        """
        SELECT id, submission_id, file_id, file_type, position
        FROM submission_files
        WHERE submission_id = ?
        ORDER BY position ASC, id ASC
        """,
        (submission_id,),
    )


async def get_submission_by_id(submission_id: int):
    return await fetch_one(
        """
        SELECT id, assignment_id, student_id, file_id, file_type, submitted_at, grade, teacher_comment, status
        FROM submissions
        WHERE id = ?
        """,
        (submission_id,),
    )


async def get_latest_submission_for_assignment(student_id: int, assignment_id: int):
    return await fetch_one(
        """
        SELECT id, assignment_id, student_id, file_id, file_type, submitted_at, grade, teacher_comment, status
        FROM submissions
        WHERE student_id = ? AND assignment_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (student_id, assignment_id),
    )


async def get_ungraded_submissions():
    return await fetch_all(
        """
        SELECT
            s.id,
            s.assignment_id,
            s.student_id,
            s.file_id,
            s.file_type,
            s.submitted_at,
            s.grade,
            s.teacher_comment,
            s.status,
            u.full_name AS student_full_name,
            a.title AS assignment_title
        FROM submissions s
        JOIN users u ON u.id = s.student_id
        JOIN assignments a ON a.id = s.assignment_id
        WHERE s.status = 'submitted'
        ORDER BY s.id DESC
        """
    )


async def grade_submission(submission_id: int, grade: str, teacher_comment: str) -> None:
    await execute(
        """
        UPDATE submissions
        SET grade = ?, teacher_comment = ?, status = 'graded'
        WHERE id = ?
        """,
        (grade, teacher_comment, submission_id),
    )
