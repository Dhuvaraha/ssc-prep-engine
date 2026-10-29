"""Original reviewed-development pack; not registered or learner-published.

Rates are exact fractions. Numerical variants test near transfer, not broad mastery.
"""
from fractions import Fraction
from app.services.teaching_journey import JourneyContent

LESSON = {
    'objective': 'Conserve completed work when workers join, leave or alternate.',
    'prerequisites': [
        'Choose one whole job. A worker taking 10 days completes 1/10 job per day.',
        'Rate is work per day; duration is days per job. Their units are different.',
        'Assume constant productivity, the same job and no interference between workers.',
    ],
    'worked_example': [
        'A needs 12 days and B needs 18. Choose 36 work units: A does 3 per day, B does 2.',
        'Together they do 5 units per day, so 36/5 = 7.2 days. This is less than either solo time.',
        'If A first works alone for 3 days, 9 units are done and 27 remain.',
        'The joint stage takes 27/5 = 5.4 more days. Total elapsed time is 3 + 5.4 = 8.4 days.',
        'For a deadline, count each worker only during their active interval. Add their completed work to one job.',
        'For alternate days, count a full two-day cycle, then check who works the final partial day.',
    ],
    'shortcut': 'For simultaneous constant rates, time = 1/(1/a + 1/b) = ab/(a+b). This follows from adding work per day.',
    'limit': 'Do not add durations or use the simultaneous shortcut for a changing or alternating schedule.',
}


def number(value):
    value = Fraction(value)
    return str(value.numerator) if value.denominator == 1 else f'{value.numerator}/{value.denominator}'


def raw_item(state):
    stage, n = state['stage'], state['variant']
    k = n + 2
    if stage == 'diagnose':
        a, b = 6*k, 3*k
        values = [a+b, Fraction(a+b,2), 2*k, b]
        stem = f'A completes a job in {a} days and B in {b} days. At constant independent rates, how many days do they need together?'
        explanations = [
            f'{a+b} adds durations, but simultaneous workers add work per day.',
            f'{number(values[1])} averages durations; it does not add rates.',
            f'The rate is 1/{a} + 1/{b} = 1/{2*k} job per day, giving {2*k} days.',
            f'{b} is B alone; A also contributes, so together they finish sooner.',
        ]
        repairs = ['Write work/day for each worker before adding.', 'Use equal work units, not an average of times.',
                   'Check that the joint time is below both solo times.', 'Include both productive rates.']
        answer = 3
    elif stage == 'retry':
        a, b = 4*k, 6*k
        values = [Fraction(9*k,5), Fraction(14*k,5), Fraction(12*k,5), a+b]
        stem = f'A needs {a} days and B {b} days for one job. A works alone for {k} days, then B joins. What is the total elapsed time to finish?'
        explanations = [
            f'{number(values[0])} is the remaining joint stage only; add the first {k} days.',
            f'A completes 1/4 job. Remaining work is 3/4; joint rate is 5/{12*k}. The joint stage is {number(values[0])}, total {number(values[1])} days.',
            f'{number(values[2])} assumes both work from the start, contrary to the schedule.',
            f'{a+b} adds solo times and ignores both completed work and the joint stage.',
        ]
        repairs = ['Separate elapsed and remaining time.', 'Verify both stages add to exactly one job.',
                   'Draw the joining point on a timeline.', 'Use remaining work divided by combined rate.']
        answer = 2
    elif stage == 'transfer':
        a,b,c,deadline = 4*k,6*k,12*k,3*k
        values = [k,2*k,3*k,4*k]
        stem = f'A, B and C take {a}, {b} and {c} days respectively for one job. All start together; B and C then leave, and A finishes. If the total time is {deadline} days, after how many days did B and C leave? Assume constant independent rates.'
        explanations = [
            f'A works all {deadline} days and completes 3/4 job. B and C must supply 1/4 at rate 1/{b} + 1/{c} = 1/{4*k}, taking {k} days.',
            f'{2*k} is the completion time if all three work throughout; it is not the switching time.',
            f'{3*k} is the total deadline. Keeping all three that long would exceed one job.',
            f'{4*k} is A alone and exceeds the given deadline; it cannot be the leaving time.',
        ]
        repairs = ['Count A over the whole timeline; count B and C only before the switch.',
                   'Distinguish all-together time from the unknown switching interval.',
                   'Substitute the proposed switch into the total-work equation.',
                   'Require the switch to occur between the start and the deadline.']
        answer = 1
    elif stage == 'revision':
        k = 5*n+2  # remainder 4 of a 5-unit cycle: a genuine partial final day
        a,b,units = 4*k,6*k,12*k
        cycles = (units-1)//5
        correct = Fraction(2*cycles)+Fraction(3,2)
        values = [Fraction(units,5), 2*cycles+2, correct, 2*cycles]
        stem = f'A needs {a} days and B {b} days for a job. They work on alternate days, A first, at constant rates. They stop immediately when finished. What is the total time?'
        explanations = [
            f'{number(values[0])} assumes simultaneous work; only one worker is active each day.',
            f'{values[1]} rounds to a full final day; B needs only half that day.',
            f'Use {units} units: A does 3/day and B 2/day. After {cycles} two-day cycles, 4 units remain. A does 3 in one day and B does the last unit in half a day: {number(correct)} days.',
            f'{values[3]} stops after complete cycles, with 4 work units unfinished.',
        ]
        repairs = ['Write the alternating schedule before using rates.', 'Divide the final work by the active worker rate.',
                   'Check the last partial day against the schedule.', 'Count the unfinished work after full cycles.']
        answer = 3
    else:
        raise ValueError('Unknown reviewed stage')
    return dict(id=stage, stem=stem, options=[number(v)+' days' for v in values],
                answer=answer, explanations=explanations, repairs=repairs)


CONTENT = JourneyContent('time-work-v1', LESSON, raw_item,
    'Choose one job or convenient work units. Mark who is active in each interval and conserve total work.')
