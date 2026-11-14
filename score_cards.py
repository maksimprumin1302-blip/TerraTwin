"""Pure, testable view model of evidence ranking; no HTML widget injection."""

def view_rows(ranking):
    result = []
    for row in ranking:
        score = int(row['score'])
        calculation = row['calculation']
        if not 0 <= score <= 100:
            raise ValueError('Score out of bounds')
        result.append({
            'id': row['site']['id'], 'name': row['site']['name'],
            'country': row['site']['country'], 'score': score,
            'progress': score, 'coverage': int(calculation['coverage']),
            'value_text': f'{score} / 100',
            'has_missing': calculation['unknown_count'] > 0,
        })
    return result
