def dictfetchone(cursor):
    """
    Return single row from a cursor as a dict.
    """
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, cursor.fetchone()))


def dictfetchall(cursor):
    """
    Return all rows from a cursor as a dict.
    """
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
