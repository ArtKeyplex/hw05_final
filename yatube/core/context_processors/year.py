from datetime import date


def year(request):
    """Добавляет переменную с текущим годом."""
    todays_date = date.today()
    return {
        'year': todays_date.year,
    }
