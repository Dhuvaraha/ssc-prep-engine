"""Original changing-base pilot. Server-only keys; not an authenticated PYQ.

Pure journey contract, intentionally not published until application integration
and independent educational/browser review are complete.
"""
from datetime import timedelta
from decimal import Decimal

VERSION = 'changing-base-v1'
LESSON = {
    'objective': 'Name the base of each percentage and compute successive changes.',
    'prerequisites': [
        'Percent means per hundred: 20% of 150 is 20/100 × 150 = 30.',
        'After a 20% reduction, 80% remains: multiply the original amount by 0.80.',
        'A second percentage uses its stated base, which may be the new amount.',
        'A price 30% above cost is cost multiplied by 1.30. Cost 100 would give a list price of 130.',
        'The customer payment and the seller receipt differ when a platform takes a fee.',
    ],
    'worked_example': [
        'A price of 200 is reduced by 10%, then by 20%.',
        'First discount: 10% of 200 = 20, leaving 180.',
        'Second discount: 20% of 180 = 36, leaving 144.',
        'The total reduction is 56/200 = 28%, not 30%.',
        'Fee bridge: if a customer pays 200 and a platform keeps 5%, the fee is 10 and the seller receives 190.',
        'If that item cost 160, profit is 30. Profit percentage uses cost: 30/160 × 100 = 18.75%.',
    ],
    'shortcut': 'Multiply remaining fractions: 200 × 0.90 × 0.80 = 144.',
    'limit': 'A fixed fee is subtracted as money; it is not a percentage multiplier.',
}

# Every option has its actual calculation and its relevance to this stem.
ITEMS = [
    {
        'id': 'diagnose', 'stem': 'A price of 500 receives discounts of 20%, then 10%. What is paid?',
        'options': ['350', '360', '400', '450'], 'answer': 2,
        'explanations': [
            '350 subtracts 30% of 500. The second discount is on 400, so adding rates is invalid here.',
            '360 = 500 × 0.80 × 0.90. The second discount is 40, not 50.',
            '400 is the price after only the first discount. The second reduction still applies.',
            '450 applies only the 10% discount to 500 and omits the first reduction.',
        ],
        'repairs': ['Name each new base before calculating the next reduction.',
                    'Check your reasoning by stating why the second discount is 40.',
                    'Draw two boxes, one for each discount; do not stop at the first box.',
                    'Preserve both changes in their stated order.'],
    },
    {
        'id': 'retry', 'stem': 'An item priced at 800 is reduced by 25%, then 10%. What is paid?',
        'options': ['520', '540', '600', '720'], 'answer': 2,
        'explanations': [
            '520 treats the total discount as 35% of 800, using the wrong base for the second reduction.',
            '540 = 800 × 0.75 × 0.90. The second reduction is 60 from the remaining 600.',
            '600 is the intermediate price after 25% off; it omits the second discount.',
            '720 takes only 10% off the initial 800; it omits the 25% discount.',
        ],
        'repairs': ['Track the base: 800 becomes 600 before the second reduction.',
                    'Explain the two bases without looking at the worked example.',
                    'Complete the second step after reaching 600.',
                    'Apply the first reduction before the second.'],
    },
    {
        'id': 'transfer', 'stem': 'A seller lists an item 40% above cost, offers discounts of 10% and 20%, and pays a platform 5% of the customer payment. What is the final result relative to cost?',
        'options': ['4.24% loss', '0.8% profit', '6.9% loss', '4.2% loss'], 'answer': 1,
        'explanations': [
            'For cost 100, receipt is 140 × 0.90 × 0.80 × 0.95 = 95.76: a 4.24% loss.',
            '100.8 is the customer payment before the fee. Calling this profit omits the platform deduction.',
            '140 × 0.70 × 0.95 = 93.1 incorrectly adds the two discount rates.',
            '100.8 − 5 = 95.8 wrongly bases the fee on cost 100. The fee is 5% of 100.8.',
        ],
        'repairs': ['Explain why the fee base is the customer payment.',
                    'Separate what the customer pays from what the seller receives.',
                    'Use two remaining-price multipliers, not one summed discount.',
                    'Write “5% of customer payment” before computing the fee.'],
    },
    {
        'id': 'revision', 'stem': 'A price of 1200 is reduced by 15%, then 20%. What is the final price?',
        'options': ['780', '816', '960', '1020'], 'answer': 2,
        'explanations': [
            '780 subtracts 35% of 1200, incorrectly adding successive discounts.',
            '816 = 1200 × 0.85 × 0.80. The second discount is 204 from 1020.',
            '960 applies only the 20% discount to the starting price.',
            '1020 stops after the first discount and omits the second.',
        ],
        'repairs': ['Revisit changing bases, then use another fresh check.',
                    'State the intermediate base and explain the second reduction.',
                    'Include both discounts.', 'Complete the second reduction.'],
    },
]


def question(stage):
    item = next(i for i in ITEMS if i['id'] == stage)
    return {k: item[k] for k in ('id', 'stem', 'options')}


def assess(stage, selected, *, assisted, previously_answered, now):
    if type(assisted) is not bool or type(previously_answered) is not bool:
        raise ValueError('Evidence flags must be booleans')
    if type(selected) is not int or selected not in (1, 2, 3, 4):
        raise ValueError('Choose one of the four options')
    item = next(i for i in ITEMS if i['id'] == stage)
    correct = selected == item['answer']
    independent = correct and not assisted and not previously_answered
    # A repeat can help learning, but cannot manufacture independent mastery.
    return {
        'version': VERSION, 'correct': correct, 'independent_evidence': independent,
        'correct_option': item['answer'],
        'four_option_explanations': item['explanations'],
        'repair': item['repairs'][selected - 1],
        'revision_due_at': (now + timedelta(days=1)).isoformat() if independent and stage == 'transfer' else None,
        'next': ('revision_recorded' if stage == 'revision' else 'revision_scheduled' if stage == 'transfer' else 'transfer' if stage == 'retry' else 'retry')
                if independent else 'repair_then_fresh_check',
        'exam_readiness': None,
    }


def raw_item(state):
    base = next(i for i in ITEMS if i['id'] == state['stage'])
    n = state['variant']
    if not n:
        return base
    # Fresh quantities, same explicit objective. These are near-transfer checks,
    # not independent evidence of whole-topic or examination readiness.
    amount = Decimal(400 + n * 100)
    a, b = Decimal(20), Decimal(15)
    correct = amount * (1-a/100) * (1-b/100)
    values = [amount*(1-(a+b)/100), correct, amount*(1-a/100), amount*(1-b/100)]
    if state['stage'] == 'transfer':
        markup = Decimal(40+n)
        payment = (100+markup)*Decimal('.9')*Decimal('.8')
        receipt = payment*Decimal('.95')
        values = [receipt-100,payment-100,(100+markup)*Decimal('.7')*Decimal('.95')-100,payment-105]
        labels = [f'{abs(v).normalize():f}% '+('profit' if v>=0 else 'loss') for v in values]
        return dict(id='transfer', stem=f'A seller lists an item {markup}% above cost, discounts it by 10% then 20%, and pays 5% of the customer payment as a fee. What is the result relative to cost?',
            options=labels,answer=1,explanations=[f'Use cost 100: payment {payment}, receipt {receipt}; compare receipt with cost.',
            'This omits the fee from customer payment.','This adds the discount rates instead of changing the base.',
            'This incorrectly subtracts a fee of 5 from a cost base of 100.'],repairs=base['repairs'])
    return dict(id=state['stage'],stem=f'A price of {amount} receives successive discounts of 20% and 15%. What is paid?',
        options=[f'{v.normalize():f}' for v in values],answer=2,
        explanations=[f'{values[0]} adds the rates, using the wrong second base.',
        f'{correct} = {amount} × 0.80 × 0.85. The second base is {values[2]}.',
        f'{values[2]} stops after the first discount.',f'{values[3]} omits the first discount.'],
        repairs=['Name the new base before applying the second reduction.',
                 'Explain both bases without looking at the worked example.',
                 'Complete the second reduction after the first.',
                 'Apply both reductions in their stated order.'])


from app.services.teaching_journey import JourneyContent

CONTENT = JourneyContent(VERSION, LESSON, raw_item,
    "Name the amount each percentage applies to, then multiply the fractions remaining.")
