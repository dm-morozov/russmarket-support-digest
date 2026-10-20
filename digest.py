"""Read-only support digest. Python 3.10+, standard library only."""
import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Время должно быть строкой ISO 8601')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:[+-]\d{2}:\d{2}|Z)', value):
        raise ValueError('Требуется время YYYY-MM-DDTHH:MM:SS[.ffffff] с UTC-смещением или Z')
    if not value.endswith('Z') and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise ValueError('Некорректное UTC-смещение')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Требуется дата со смещением часового пояса')
    return result


def calendar_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Требуется календарная дата YYYY-MM-DD')
    return date.fromisoformat(value)


def review(case, reason):
    return {**case, 'priority': 2, 'decision': 'Нужна ручная проверка данных',
            'reasons': [reason], 'review_required': True,
            'checks': ['Сверить первоисточники CRM и переписки с ответственным.'],
            'actions': ['Уточнить недостающие или противоречивые сведения; не закрывать операцию и не менять CRM автоматически.']}


def analyze(case, now):
    """Structured CRM fields are authoritative; chat text is evidence, never code."""
    kind = case['kind']
    crm = case['crm']
    if kind not in {'onboarding', 'dismissal', 'delivery'}:
        return review(case, f'Для типа «{kind}» нет согласованного правила.')
    if case['chat'].get('conflicts_with_crm'):
        return review(case, 'При нормализации отмечено противоречие переписки и CRM; текст сам по себе не отменяет подтверждение.')
    if not crm['evidence'].strip() or not case['chat']['evidence'].strip():
        return review(case, 'Не хватает описания CRM или переписки; отсутствие сведений не означает отсутствие проблемы.')
    priority, decision = 4, 'Проверить данные'
    checks, actions = [], []
    if kind == 'onboarding':
        if crm.get('first_day') is None or crm.get('documents_confirmed') is None:
            return review(case, 'Не указана дата первого выхода или неизвестно подтверждение документов.')
        first_day = calendar_date(crm['first_day'])
        if not isinstance(crm['documents_confirmed'], bool):
            raise ValueError('documents_confirmed должен быть bool')
        if not crm['documents_confirmed']:
            priority = 3 if first_day > now.date() else 2
            decision = 'Нужно вмешательство: документы не подтверждены'
            checks = ['Проверить получение, комплектность и пригодность документов у ответственного руководителя.']
            actions = ['Сегодня запросить подтверждение руководителя и недостающие документы; зафиксировать результат в CRM до первого выхода.']
        else:
            decision = 'Вмешательство по документам не требуется'
    elif kind == 'dismissal':
        if crm.get('last_day') is None or crm.get('manager_confirmed') is None:
            return review(case, 'Не указана дата последнего рабочего дня или неизвестно подтверждение руководителя.')
        last_day = calendar_date(crm['last_day'])
        if not isinstance(crm['manager_confirmed'], bool):
            raise ValueError('manager_confirmed должен быть bool')
        if not crm['manager_confirmed']:
            priority = 2 if last_day <= now.date() else 3
            decision = 'Нужно вмешательство: нет подтверждения руководителя'
            checks = ['Получить прямое подтверждение ответственного руководителя и проверить дату последнего рабочего дня.']
            actions = ['Связаться с руководителем сегодня и занести подтверждение в CRM; слова сотрудника не считать основанием для закрытия операции.']
        else:
            decision = 'Вмешательство по подтверждению не требуется'
    else:
        status = crm.get('status')
        if status not in {'in_transit', 'accepted'}:
            return review(case, f'Неизвестный или отсутствующий статус доставки: {json.dumps(status, ensure_ascii=False)}.')
        accepted = timestamp(crm['accepted_at']) if crm.get('accepted_at') else None
        if accepted is not None and accepted > now:
            raise ValueError('Подтверждение приёмки находится в будущем')
        if status == 'in_transit' and accepted is not None:
            return review(case, 'Статус «В пути» противоречит заполненному времени приёмки в CRM.')
        if status == 'accepted' and accepted is not None:
            priority, decision = 4, 'Вмешательство не требуется: приёмка подтверждена в CRM'
            checks = ['При плановой сверке проверить запись приёмки и количество; внеплановое действие не требуется.']
            actions = ['Не включать в срочные задачи; сохранить подтверждение и оставить случай в сводке как завершённый.']
        elif status == 'accepted':
            return review(case, 'Статус «Принято» без времени подтверждения приёмки.')
        else:
            if not crm.get('due_at'):
                return review(case, 'Для незавершённой доставки не указан срок: срочность определить нельзя.')
            due = timestamp(crm['due_at'])
            eta = timestamp(case['chat']['eta_at']) if case['chat'].get('eta_at') else None
            if due <= now or (eta is not None and eta > due):
                priority = 1
                decision = 'Нужно вмешательство: срок доставки наступил или есть риск опоздания'
                checks = ['Проверить у курьера фактическое местоположение и ETA, у получателя — факт приёмки.']
                actions = ['Приоритетно проверить эту доставку: предупредить ответственного на точке, согласовать новый срок или резервный вариант и зафиксировать задержку в CRM.']
            else:
                priority, decision = 3, 'Наблюдать: доставка ещё не подтверждена'
                checks = ['Проверить приёмку к согласованному сроку.']
                actions = ['Повторить сверку к сроку доставки; при риске опоздания связаться с ответственным.']
    if not checks:
        checks = ['Плановая сверка подтверждений CRM.']
        actions = ['Сохранить в ежедневной сводке.']
    return {**case, 'priority': priority, 'decision': decision, 'reasons': [decision],
            'review_required': False, 'checks': checks, 'actions': actions}


def build(payload):
    if not isinstance(payload, dict):
        raise ValueError('Вход должен быть JSON-объектом')
    now = timestamp(payload['as_of'])
    if not isinstance(payload.get('cases'), list):
        raise ValueError('cases должен быть массивом')
    if len(payload['cases']) > 100:
        raise ValueError('Демо принимает не более 100 случаев')
    if not isinstance(payload.get('context', ''), str):
        raise ValueError('context должен быть текстом')
    cases = []
    for original in payload['cases']:
        if not isinstance(original, dict):
            raise ValueError('Каждый случай должен быть объектом')
        for name in ['id', 'kind']:
            if not isinstance(original.get(name), str) or not original[name].strip():
                raise ValueError(f'{name} должен быть непустой строкой')
        case = dict(original)
        for source in ['crm', 'chat']:
            if not isinstance(case.get(source), dict):
                raise ValueError(f'{source} должен быть объектом')
            case[source] = {'evidence': '', **case[source]}
            if not isinstance(case[source]['evidence'], str):
                raise ValueError('Описание источников должно быть текстом')
        for name in ['documents_confirmed', 'manager_confirmed']:
            if case['crm'].get(name) is not None and type(case['crm'][name]) is not bool:
                raise ValueError(f'{name} должен быть bool или null')
        if case['crm'].get('status') is not None and not isinstance(case['crm']['status'], str):
            raise ValueError('status должен быть строкой или null')
        if type(case['chat'].get('conflicts_with_crm', False)) is not bool:
            raise ValueError('conflicts_with_crm должен быть bool')
        for name in ['first_day', 'last_day']:
            if case['crm'].get(name) is not None:
                if not isinstance(case['crm'][name], str):
                    raise ValueError(f'{name} должен быть датой YYYY-MM-DD')
                calendar_date(case['crm'][name])
        for source, name in [('crm', 'due_at'), ('crm', 'accepted_at'), ('chat', 'eta_at')]:
            if case[source].get(name) is not None:
                timestamp(case[source][name])
        cases.append(case)
    ids = [case['id'] for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError('Повторяющийся идентификатор случая')
    results = []
    for case in cases:
        result = analyze(case, now)
        if result['review_required'] and case['kind'] == 'delivery' and case['crm'].get('due_at'):
            due = timestamp(case['crm']['due_at'])
            eta = timestamp(case['chat']['eta_at']) if case['chat'].get('eta_at') else None
            if due <= now or (eta is not None and eta > due):
                result['priority'] = 1
                result['reasons'].append('Согласованный срок уже наступил или ETA позже срока: ручную проверку нельзя откладывать.')
        results.append(result)
    results.sort(key=lambda c: (c['priority'], c['id']))
    return {'as_of': now.isoformat(), 'context': payload.get('context', ''), 'cases': results}


def markdown(result):
    lines = ['# Ежедневная сводка support-отдела', '', f"Срез: {result['as_of']}", '',
             'Приоритеты: 1 — начать сейчас; 2 — сегодня; 3 — до ближайшего срока; 4 — плановая сверка.', '',
             'CRM содержит подтверждённые статусы. Сведения из чата не меняют CRM автоматически.', '']
    if result.get('context'):
        lines += [result['context'], '']
    for case in result['cases']:
        lines += [f"## {case['id']} · приоритет {case['priority']}", '', case['decision'], '',
                  f"**CRM:** {case['crm']['evidence']}", '',
                  f"**Только переписка:** {case['chat']['evidence']}", '',
                  '**Проверить:** ' + ' '.join(case['checks']), '',
                  '**Следующий шаг:** ' + ' '.join(case['actions']), '']
        if case.get('review_required'):
            lines += ['**Причина ручной проверки:** ' + ' '.join(case['reasons']), '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--format', choices=['markdown', 'json'], default='markdown')
    args = parser.parse_args()
    try:
        result = build(json.loads(args.input.read_text(encoding='utf-8-sig')))
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.format == 'json' else markdown(result))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f'Ошибка входных данных: {error}\n')


if __name__ == '__main__':
    main()
