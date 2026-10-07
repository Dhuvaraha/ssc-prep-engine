-- Phase 4B deterministic Quant unique-depth seed.
-- Idempotent via source_question_id. All rows are original generated private study content.

WITH topic_map AS (
  SELECT t.id AS topic_id, s.id AS subject_id, s.slug AS subject_slug, t.slug AS topic_slug
  FROM topics t
  JOIN subjects s ON s.id = t.subject_id
  JOIN exams e ON e.id = s.exam_id
  WHERE e.slug = 'ssc-cgl-tier-1'
),
generated AS (
  -- Mensuration: rectangle area
  SELECT tm.topic_id, tm.subject_id, 'mensuration'::text topic_slug, g,
         format('A rectangle has length %s cm and breadth %s cm. What is its area?', 10+g, 5+(g%17)) question_text,
         ((10+g)*(5+(g%17)))::numeric answer,
         'rectangle-area'::text pattern_type, 'Area of rectangle'::text subtopic,
         1 + (g%3) difficulty, 35 expected_time,
         format('Area = length × breadth = %s × %s = %s cm².',10+g,5+(g%17),(10+g)*(5+(g%17))) explanation,
         'Multiply length and breadth.'::text fast_method
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='mensuration'

  UNION ALL
  -- Trains: pole crossing
  SELECT tm.topic_id, tm.subject_id, 'trains', g,
         format('A train %s m long runs at %s km/h. How many seconds does it take to cross a pole?',100+5*g,36+18*(g%5)),
         round((100+5*g)::numeric / ((36+18*(g%5))::numeric*5/18),2),
         'train-crosses-pole','Pole crossing',1+(g%3),45,
         format('Convert %s km/h to m/s and use time = train length ÷ speed.',36+18*(g%5)),
         'For a pole, distance covered equals the train length.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='trains'

  UNION ALL
  -- Boats & streams: downstream speed
  SELECT tm.topic_id, tm.subject_id, 'boats-and-streams', g,
         format('A boat moves at %s km/h in still water and the stream speed is %s km/h. What is its downstream speed?',12+(g%20),1+((g*7)%11)),
         (13+(g%20)+((g*7)%11))::numeric,
         'downstream-speed','Boat and stream speed',1+(g%3),30,
         format('Downstream speed = still-water speed + stream speed = %s + %s.',12+(g%20),1+((g*7)%11)),
         'Downstream: add the stream speed.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='boats-and-streams'

  UNION ALL
  -- Mixture & alligation: weighted concentration
  SELECT tm.topic_id, tm.subject_id, 'mixture-and-alligation', g,
         format('%s parts of a %s%% solution are mixed with %s parts of a %s%% solution. What is the concentration of the mixture?',
                1+(g%5),10+(g%30),1+((g*3)%7),60+(g%31)),
         round((((1+(g%5))*(10+(g%30)) + (1+((g*3)%7))*(60+(g%31)))::numeric /
                ((1+(g%5)) + (1+((g*3)%7)))),2),
         'weighted-mixture','Weighted concentration',2+(g%2),55,
         'Use the weighted average: total solute percentage-units divided by total parts.',
         'Weighted mean = (p₁c₁ + p₂c₂)/(p₁+p₂).'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='mixture-and-alligation'

  UNION ALL
  -- Trigonometry: exact standard-angle values
  SELECT tm.topic_id, tm.subject_id, 'trigonometry', g,
         format('Evaluate %s·sin 30° + %s·cos 60°.',1+g,2+(g%17)),
         round(((1+g + 2+(g%17))::numeric/2),2),
         'standard-angle-evaluation','Standard trigonometric values',1+(g%3),35,
         'sin 30° = 1/2 and cos 60° = 1/2, so add the coefficients and divide by 2.',
         'Replace standard-angle ratios before calculating.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='trigonometry'

  UNION ALL
  -- Elementary Statistics: arithmetic mean
  SELECT tm.topic_id, tm.subject_id, 'elementary-statistics', g,
         format('Find the arithmetic mean of %s, %s, %s, %s and %s.',g,g+2,g+4,g+6,g+8),
         (g+4)::numeric,
         'arithmetic-mean','Mean',1+(g%3),35,
         format('These five equally spaced values are centred at %s, so their mean is %s.',g+4,g+4),
         'For an odd count of equally spaced terms, the middle term is the mean.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='elementary-statistics'

  UNION ALL
  -- Pipes & cisterns: two filling pipes
  SELECT tm.topic_id, tm.subject_id, 'pipes-and-cisterns', g,
         format('Pipe A fills a tank in %s minutes and pipe B in %s minutes. If both are opened together, how many minutes are needed?',10+(g%20),12+((g*7)%25)),
         round(((10+(g%20))::numeric*(12+((g*7)%25))) /
               ((10+(g%20)) + (12+((g*7)%25)))::numeric,2),
         'two-inlet-pipes','Combined filling rate',2+(g%2),50,
         'Add the two filling rates and take the reciprocal.',
         'Together time for two inlet pipes = ab/(a+b).'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='pipes-and-cisterns'

  UNION ALL
  -- Data Interpretation: total from a four-category table in prose
  SELECT tm.topic_id, tm.subject_id, 'data-interpretation', g,
         format('A shop sold %s, %s, %s and %s units in four successive weeks. What was the total sale?',100+g,80+2*g,120+(g%31),90+(g%23)),
         ((100+g)+(80+2*g)+(120+(g%31))+(90+(g%23)))::numeric,
         'table-total','Four-value data total',1+(g%3),45,
         'Add the four weekly values to obtain the total.',
         'For a total question, sum only the requested categories.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='data-interpretation'

  UNION ALL
  -- Simple Interest
  SELECT tm.topic_id, tm.subject_id, 'simple-interest', g,
         format('Find the simple interest on ₹%s at %s%% per annum for %s years.',1000+25*g,4+(g%9),1+(g%5)),
         round(((1000+25*g)::numeric*(4+(g%9))*(1+(g%5))/100),2),
         'simple-interest-direct','Direct SI',1+(g%3),40,
         'Simple interest = Principal × Rate × Time ÷ 100.',
         'Use SI = PRT/100.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='simple-interest'

  UNION ALL
  -- Coordinate Geometry: midpoint
  SELECT tm.topic_id, tm.subject_id, 'coordinate-geometry', g,
         format('Find the midpoint of the points (%s, %s) and (%s, %s).',g,(g%13)-6,g+2,(g%13)-2),
         NULL::numeric,
         'midpoint','Midpoint of two points',1+(g%3),35,
         format('Midpoint = ((x₁+x₂)/2,(y₁+y₂)/2) = (%s, %s).',g+1,(g%13)-4),
         'Average the x-coordinates and y-coordinates separately.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='coordinate-geometry'

  UNION ALL
  -- Heights & distances: 45-degree elevation
  SELECT tm.topic_id, tm.subject_id, 'heights-and-distances', g,
         format('From a point %s m from the foot of a vertical tower, the angle of elevation of its top is 45°. Find the tower height.',10+g),
         (10+g)::numeric,
         'tan45-height','Height using tan 45°',1+(g%3),35,
         'tan 45° = height/base = 1, so height equals the horizontal distance.',
         'At 45°, opposite = adjacent.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='heights-and-distances'

  UNION ALL
  -- LCM & HCF: structured pair with exact HCF
  SELECT tm.topic_id, tm.subject_id, 'lcm-and-hcf', g,
         format('Find the HCF of %s and %s.',6*(g+1),9*(g+1)),
         (3*(g+1))::numeric,
         'hcf-common-factor','HCF',1+(g%3),30,
         format('HCF(6n,9n)=3n. Here n=%s, so HCF=%s.',g+1,3*(g+1)),
         'Factor out the common multiplier first.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='lcm-and-hcf'
),
prepared AS (
  SELECT *,
    CASE
      WHEN topic_slug='coordinate-geometry' THEN format('(%s, %s)',g+1,(g%13)-4)
      ELSE trim(to_char(answer,'FM999999990.00'))
    END AS answer_text,
    CASE
      WHEN topic_slug='coordinate-geometry' THEN format('(%s, %s)',g+2,(g%13)-4)
      ELSE trim(to_char(answer + greatest(1,abs(answer)*0.1),'FM999999990.00'))
    END AS d1,
    CASE
      WHEN topic_slug='coordinate-geometry' THEN format('(%s, %s)',g+1,(g%13)-3)
      ELSE trim(to_char(greatest(0.01,answer - greatest(1,abs(answer)*0.1)),'FM999999990.00'))
    END AS d2,
    CASE
      WHEN topic_slug='coordinate-geometry' THEN format('(%s, %s)',g,(g%13)-4)
      ELSE trim(to_char(answer + greatest(2,abs(answer)*0.2),'FM999999990.00'))
    END AS d3,
    ((g-1)%4) AS shift
  FROM generated
),
rows AS (
  SELECT *,
         ARRAY[answer_text,d1,d2,d3]::text[] AS raw_options,
         1 + ((4-shift)%4) AS correct_pos,
         format('phase4b-quant-%s-%s',topic_slug,g) AS source_id
  FROM prepared
),
inserted AS (
  INSERT INTO questions (
    exam_id, subject_id, topic_id, subtopic, pattern_type, question_text,
    correct_option, explanation, fast_method, difficulty, expected_time_seconds,
    source_type, source_reference, source_question_id, visibility, verification_status
  )
  SELECT e.id, r.subject_id, r.topic_id, r.subtopic, r.pattern_type, r.question_text,
         r.correct_pos, r.explanation, r.fast_method, r.difficulty, r.expected_time,
         'generated','phase4b-deterministic',r.source_id,'private','verified'
  FROM rows r
  JOIN exams e ON e.slug='ssc-cgl-tier-1'
  WHERE NOT EXISTS (
    SELECT 1 FROM questions q WHERE q.source_question_id=r.source_id
  )
  RETURNING id, source_question_id
)
INSERT INTO question_options(question_id,position,text)
SELECT i.id, p,
       r.raw_options[1 + ((p + r.shift - 1)%4)]
FROM inserted i
JOIN rows r ON r.source_id=i.source_question_id
CROSS JOIN generate_series(1,4) p;
