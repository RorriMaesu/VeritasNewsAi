# src/utils/validation.py
def validate_script(script: Dict) -> bool:
    requirements = {
        'title': (lambda x: 10 <= len(x) <= 80),
        'duration': (lambda x: 180 <= x <= 300),
        'brand_mentions': (lambda x: x >= 2)
    }
    return all(check(script.get(key)) for key, check in requirements.items())