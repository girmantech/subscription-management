from rest_framework_simplejwt.tokens import RefreshToken

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


def generate_refresh_token(customer):
    refresh = RefreshToken.for_user(customer)

    del refresh['user_id']
    refresh['customer_id'] = customer.id

    return {
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
    }
