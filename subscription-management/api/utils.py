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
    refresh['id'] = customer.id
    refresh['name'] = customer.name
    refresh['phone'] = customer.phone
    refresh['email'] = customer.email
    refresh['currency'] = customer.currency.code
    refresh['address1'] = customer.address1
    refresh['address2'] = customer.address2
    refresh['city'] = customer.city
    refresh['postal_code'] = customer.postal_code
    refresh['created_at'] = customer.created_at
    refresh['deleted_at'] = customer.deleted_at

    return {
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
    }
