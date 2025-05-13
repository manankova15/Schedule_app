import pytest
from api.templatetags.custom_filters import split, format_date, get_shift_info, get_shift_type_display

@pytest.mark.django_db
class TestCustomFilters:
    def test_split_filter(self):
        """Test the split filter for template tags"""
        test_string = "apple,banana,orange"
        result = split(test_string, ",")
        assert result == ["apple", "banana", "orange"]

        test_string = "apple|banana|orange"
        result = split(test_string, "|")
        assert result == ["apple", "banana", "orange"]

        test_string = "apple"
        result = split(test_string, ",")
        assert result == ["apple"]

        test_string = ""
        result = split(test_string, ",")
        assert result == []

        result = split(None, ",")
        assert result == []

    def test_format_date(self):
        from datetime import date

        today = date.today()
        formatted_date = format_date(today)
        assert formatted_date == today.strftime("%d.%m.%Y")

        test_date = date(2023, 5, 1)
        formatted_date = format_date(test_date)
        assert formatted_date == "01.05.2023"

        assert format_date(None) == ""

    def test_get_shift_info(self):
        morning_info = get_shift_info("morning")
        assert morning_info["name"] == "Утро"
        assert morning_info["time"] == "8:00-14:00"
        assert morning_info["color"] == "success"

        evening_info = get_shift_info("evening")
        assert evening_info["name"] == "Вечер"
        assert evening_info["time"] == "14:00-20:00"
        assert evening_info["color"] == "primary"

        night_info = get_shift_info("night")
        assert night_info["name"] == "Ночь"
        assert night_info["time"] == "20:00-8:00"
        assert night_info["color"] == "danger"

        unknown_info = get_shift_info("unknown")
        assert unknown_info["name"] == "Неизвестно"
        assert unknown_info["time"] == ""
        assert unknown_info["color"] == "secondary"

    def test_get_shift_type_display(self):
        assert get_shift_type_display("morning") == "Утро (8:00-14:00)"
        assert get_shift_type_display("evening") == "Вечер (14:00-20:00)"
        assert get_shift_type_display("night") == "Ночь (20:00-8:00)"
        assert get_shift_type_display("unknown") == "Неизвестно"
