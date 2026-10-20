"""Synthetic, non-personal demonstration changes to the four assignment cases."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def examples():
    original = json.loads((ROOT / 'examples/monday.json').read_text(encoding='utf-8'))
    confirmed = copy.deepcopy(original)
    confirmed['cases'][0]['crm'].update(documents_confirmed=True, evidence='Учебное изменение CRM: руководитель подтвердил получение и комплектность документов.')
    confirmed['cases'][1]['crm'].update(manager_confirmed=True, evidence='Учебное изменение CRM: получено прямое подтверждение ответственного руководителя, последний день сегодня.')
    confirmed['cases'][2]['crm'].update(status='accepted', accepted_at=original['as_of'], evidence='Учебное изменение CRM: приёмка подтверждена в 10:00, статус «Принято».')
    confirmed['cases'][0]['chat']['evidence'] = 'Учебное сообщение сотрудника: документы переданы, после этого руководитель подтвердил комплектность в CRM.'
    confirmed['cases'][2]['chat'] = {'evidence': 'Учебное сообщение получателя: доставка завершена; новое подтверждение приёмки записано в CRM.'}
    uncertain = copy.deepcopy(original)
    uncertain['cases'][0]['crm']['documents_confirmed'] = None
    uncertain['cases'][0]['crm']['evidence'] = 'Дата первого выхода — завтра; подтверждение документов неизвестно.'
    uncertain['cases'][1]['crm']['manager_confirmed'] = True
    uncertain['cases'][1]['crm']['evidence'] = 'В CRM стоит подтверждение руководителя.'
    uncertain['cases'][1]['chat'].update(conflicts_with_crm=True, evidence='Учебное сообщение руководителя: подтверждение в CRM ошибочно, требуется уточнение.')
    uncertain['cases'][2]['crm']['status'] = 'unknown'
    uncertain['cases'][2]['crm']['evidence'] = 'Статус доставки не распознан при выгрузке.'
    return {'original': original, 'confirmed': confirmed, 'uncertain': uncertain}
