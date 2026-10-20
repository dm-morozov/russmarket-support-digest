"""Generate expected browser results from Python; do not hand-edit expectations."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from digest import build
from scenarios import examples


def fixtures():
    output = []
    def add(name, payload):
        original = copy.deepcopy(payload)
        try:
            expected = build(payload)
            result = {'name': name, 'input': original, 'valid': True, 'expected': expected}
        except (ValueError, TypeError, KeyError):
            result = {'name': name, 'input': original, 'valid': False}
        assert payload == original, name
        output.append(result)
    for name, payload in examples().items():
        add('preset/' + name, payload)
    base = examples()['original']
    for kind, index, field, day in [('onboarding', 0, 'documents_confirmed', 'first_day'), ('dismissal', 1, 'manager_confirmed', 'last_day')]:
        for flag in [False, True, None, 'absent']:
            for deadline in ['2026-10-18', '2026-10-19', '2026-10-20', '2026-11-01', None]:
                payload = copy.deepcopy(base)
                payload['cases'] = [copy.deepcopy(base['cases'][index])]
                case = payload['cases'][0]
                case['id'] = 'OTHER-42'
                case['crm'][day] = deadline
                if flag == 'absent':
                    case['crm'].pop(field)
                else:
                    case['crm'][field] = flag
                add(f'{kind}/{flag}/{deadline}', payload)
    for status in ['in_transit', 'accepted', 'unknown', None, '', "can't confirm"]:
        for due in ['2026-10-19T09:59:59+03:00', base['as_of'], '2026-10-19T10:00:01+03:00', None]:
            for accepted in [None, '2026-10-19T09:20:00+03:00', '2026-10-19T10:00:01+03:00']:
                for eta in [None, '2026-10-19T09:00:00+03:00', '2026-10-19T13:00:00+03:00']:
                    payload = copy.deepcopy(base)
                    payload['cases'] = [copy.deepcopy(base['cases'][2])]
                    c = payload['cases'][0]
                    c['id'] = 'NEW-DELIVERY'
                    c['crm'].update(status=status, due_at=due, accepted_at=accepted)
                    c['chat']['eta_at'] = eta
                    add(f'delivery/{status}/{due}/{accepted}/{eta}', payload)
    for name, value in [('empty', []), ('invalid_cases', {}), ('invalid_case', [None])]:
        add(name, {**base, 'cases': value})
    for value in [None, [], {}, 1, 'payload']:
        add('invalid/root/' + repr(value), value)
    for field, values in [('id', ['', ' ', None, 12]), ('kind', ['', None, 12, 'unknown'])]:
        for value in values:
            p = copy.deepcopy(base)
            p['cases'][0][field] = value
            add('field/' + field + '/' + repr(value), p)
    for field, value in [('context', None), ('as_of', None), ('as_of', '2026-10-19T10:00:00')]:
        add('root/' + field + '/' + repr(value), {**base, field: value})
    p = copy.deepcopy(base)
    p['cases'].append(copy.deepcopy(p['cases'][0]))
    add('duplicate_id', p)
    add('over_100_cases', {**base, 'cases': [dict(base['cases'][0], id=str(i)) for i in range(101)]})
    for source in ['crm', 'chat']:
        for value in [None, [], 'text']:
            p = copy.deepcopy(base)
            p['cases'][0][source] = value
            add('invalid/source/' + source + '/' + repr(value), p)
        for value in [None, 7, '', '   ', '<img src=x onerror=alert(1)>']:
            p = copy.deepcopy(base)
            p['cases'][0][source]['evidence'] = value
            add('evidence/' + source + '/' + repr(value), p)
    for value in [None, 'true', True, False]:
        p = copy.deepcopy(base)
        p['cases'][3]['chat']['conflicts_with_crm'] = value
        add('conflict/' + repr(value), p)
    for value in [None, 1, [], 'false']:
        p = copy.deepcopy(base)
        p['cases'][0]['crm']['documents_confirmed'] = value
        add('typed_confirmation/' + repr(value), p)
    for value in ['2026-02-30T10:00:00+03:00', '2024-02-29T10:00:00+03:00', '2026-10-19T10:00:00+01:60', '2026-10-19T24:00:00+03:00', '2026-10-19T10:00:00.1234567+03:00', '2026-10-19T07:00:00Z', '2026-10-19T07:00:00-00:00', '2026-10-19T10:00:00.000001+03:00']:
        p = copy.deepcopy(base)
        p['as_of'] = value
        p['cases'] = [copy.deepcopy(base['cases'][2])]
        add('timestamp/' + value, p)
    for value in ['2026-10-19T07:00:00Z', '2026-10-19T00:00:00-07:00', '2026-10-19T10:00:00.000001+03:00', '2026-10-19T09:59:59.999999+03:00']:
        p = copy.deepcopy(base)
        p['cases'] = [copy.deepcopy(base['cases'][2])]
        p['cases'][0]['chat'].pop('eta_at')
        p['cases'][0]['crm']['due_at'] = value
        add('boundary/' + value, p)
    p = copy.deepcopy(base)
    p['cases'] = [dict(copy.deepcopy(base['cases'][0]), id=value) for value in ['😀', '\ue000', 'А', 'A']]
    add('unicode_ids_and_sort', p)
    return output


def main():
    destination = ROOT / 'tests/generated-parity.json'
    destination.parent.mkdir(exist_ok=True)
    data = fixtures()
    destination.write_text(json.dumps(data, ensure_ascii=True), encoding='utf-8')
    print(f'Generated {len(data)} Python parity fixtures')


if __name__ == '__main__':
    main()
