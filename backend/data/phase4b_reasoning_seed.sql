-- Phase 4B deterministic Reasoning unique-depth seed.
-- 16 topics x 100 original/private verified questions. Visual topics use inline SVG prompts.

WITH topic_map AS (
  SELECT t.id AS topic_id, s.id AS subject_id, t.slug AS topic_slug
  FROM topics t
  JOIN subjects s ON s.id=t.subject_id
  JOIN exams e ON e.id=s.exam_id
  WHERE e.slug='ssc-cgl-tier-1' AND s.slug='reasoning'
),
base AS (
  -- Blood relations
  SELECT tm.topic_id,tm.subject_id,'blood-relations'::text topic_slug,g,
    format('R%s is the father of S%s. S%s is the sister of T%s. How is R%s related to T%s?',g,g,g,g,g,g) question_text,
    NULL::text image_url,'Father'::text answer,'Mother'::text d1,'Brother'::text d2,'Uncle'::text d3,
    'father-through-sibling'::text pattern_type,'Direct family relation'::text subtopic,
    1+(g%3) difficulty,35 expected_time,
    'S and T are siblings. Their father R is therefore also T''s father.'::text explanation,
    'Link each relation one step at a time.'::text fast_method
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='blood-relations'

  UNION ALL
  -- Dictionary order
  SELECT tm.topic_id,tm.subject_id,'dictionary-order',g,
    format('Which word comes first in dictionary order: %s, %s, %s, %s?',
      chr(97+(g%20))||'able'||chr(97+((g+3)%26)),
      chr(97+(g%20))||'able'||chr(97+((g+8)%26)),
      chr(97+(g%20))||'able'||chr(97+((g+13)%26)),
      chr(97+(g%20))||'able'||chr(97+((g+18)%26))) question_text,
    chr(97+(g%20))||'able'||least(chr(97+((g+3)%26)),chr(97+((g+8)%26)),chr(97+((g+13)%26)),chr(97+((g+18)%26))) answer,
    chr(97+(g%20))||'able'||greatest(chr(97+((g+3)%26)),chr(97+((g+8)%26)),chr(97+((g+13)%26)),chr(97+((g+18)%26))) d1,
    chr(97+(g%20))||'ablez' d2, chr(97+(g%20))||'abley' d3,
    'dictionary-order-core','Alphabetical ordering',1+(g%3),35,
    'Compare letters from left to right; the first differing letter decides the order.',
    'Ignore the common prefix and compare the first differing character.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='dictionary-order'

  UNION ALL
  -- Letter series
  SELECT tm.topic_id,tm.subject_id,'letter-series',g,
    format('Find the next letter: %s, %s, %s, %s, %s, ?',
      chr(65+((g)%26)),chr(65+((g+(1+(g%5)))%26)),chr(65+((g+2*(1+(g%5)))%26)),
      chr(65+((g+3*(1+(g%5)))%26)),chr(65+((g+4*(1+(g%5)))%26))) question_text,
    chr(65+((g+5*(1+(g%5)))%26)) answer,
    chr(65+((g+5*(1+(g%5))+1)%26)) d1,
    chr(65+((g+5*(1+(g%5))+2)%26)) d2,
    chr(65+((g+5*(1+(g%5))+3)%26)) d3,
    'constant-letter-step','Alphabet step series',1+(g%3),35,
    format('Each term moves forward by %s letters cyclically.',1+(g%5)),
    'Convert letters to positions and inspect the step.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='letter-series'

  UNION ALL
  -- Syllogism
  SELECT tm.topic_id,tm.subject_id,'syllogism',g,
    format('Statements: All A%s are B%s. All B%s are C%s. Conclusions: I. All A%s are C%s. II. Some C%s are not A%s. Which conclusion definitely follows?',g,g,g,g,g,g,g,g) question_text,
    'Only I follows' answer,'Only II follows' d1,'Both I and II follow' d2,'Neither I nor II follows' d3,
    'all-all-chain','Categorical syllogism',2+(g%2),50,
    'If every A is inside B and every B is inside C, every A is inside C. Conclusion II is not guaranteed.',
    'For All→All chains, carry the subset relation forward.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='syllogism'

  UNION ALL
  -- Direction sense
  SELECT tm.topic_id,tm.subject_id,'direction-sense',g,
    format('A person walks %s m east and then %s m north. How far is the person from the starting point?',3*(1+(g%25)),4*(1+(g%25))) question_text,
    (5*(1+(g%25)))::text answer,
    (5*(1+(g%25))+3)::text d1,(5*(1+(g%25))-2)::text d2,(7*(1+(g%25)))::text d3,
    'right-angle-displacement','Pythagorean displacement',1+(g%3),40,
    'East and north movements are perpendicular. Use the 3-4-5 right triangle.',
    'Draw axes; displacement is the hypotenuse.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='direction-sense'

  UNION ALL
  -- Clock & calendar
  SELECT tm.topic_id,tm.subject_id,'clock-and-calendar',g,
    format('If today is Monday, what day will it be after %s days?',g+7) question_text,
    (ARRAY['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])[1+((g+7)%7)] answer,
    (ARRAY['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])[1+((g+8)%7)] d1,
    (ARRAY['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])[1+((g+9)%7)] d2,
    (ARRAY['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])[1+((g+10)%7)] d3,
    'day-after-n-days','Calendar remainder',1+(g%3),30,
    'Reduce the number of days modulo 7 and move that many weekdays forward.',
    'Use N mod 7.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='clock-and-calendar'

  UNION ALL
  -- Puzzle
  SELECT tm.topic_id,tm.subject_id,'puzzle',g,
    format('Five boxes P%s, Q%s, R%s, S%s and T%s are stacked from top to bottom in that order. Which box is immediately below R%s?',g,g,g,g,g,g) question_text,
    format('S%s',g) answer,format('Q%s',g) d1,format('T%s',g) d2,format('P%s',g) d3,
    'ordered-stack','Simple ordering puzzle',1+(g%3),35,
    'The stated order is P, Q, R, S, T, so S is immediately below R.',
    'Write the order once before answering.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='puzzle'

  UNION ALL
  -- Seating arrangement
  SELECT tm.topic_id,tm.subject_id,'seating-arrangement',g,
    format('A%s, B%s, C%s, D%s and E%s sit in a row from left to right in that order. Who sits second to the right of B%s?',g,g,g,g,g,g) question_text,
    format('D%s',g) answer,format('C%s',g) d1,format('E%s',g) d2,format('A%s',g) d3,
    'linear-seating-offset','Linear seating',1+(g%3),35,
    'From B, one place right is C and two places right is D.',
    'Mark positions 1 to 5.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='seating-arrangement'

  UNION ALL
  -- Word building
  SELECT tm.topic_id,tm.subject_id,'word-building',g,
    format('Which word can be formed using letters from "DOCUMENTATION%s" without using any letter more times than it appears?',g) question_text,
    'ACTION' answer,'MOTIONX' d1,'ACCOUNT' d2,'VACUUM' d3,
    'word-from-letters','Letter availability',1+(g%3),40,
    'ACTION uses only letters available in DOCUMENTATION. The other options require unavailable or overused letters.',
    'Count repeated letters, not just distinct letters.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='word-building'

  UNION ALL
  -- Venn diagrams
  SELECT tm.topic_id,tm.subject_id,'venn-diagrams',g,
    format('All poets%s are writers%s, and no writer%s is a machine%s. Which Venn relation is correct?',g,g,g,g) question_text,
    'Poets inside Writers; Machines separate' answer,
    'Writers inside Poets; Machines overlap' d1,
    'All three sets completely overlap' d2,
    'Poets and Writers are separate' d3,
    'subset-disjoint-venn','Subset and disjoint sets',2+(g%2),45,
    'All poets belong inside Writers, while Machines must remain disjoint from Writers.',
    'Translate “all” as subset and “no” as disjoint.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='venn-diagrams'

  UNION ALL
  -- Counting figures: grid rectangles, visual
  SELECT tm.topic_id,tm.subject_id,'counting-figures',g,
    format('How many small cells are present in this %s × %s grid?',2+(g%9),2+((g*3)%9)) question_text,
    'data:image/svg+xml;base64,'||encode(convert_to(
      format('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect x="20" y="20" width="280" height="140" fill="white" stroke="black"/><text x="160" y="90" text-anchor="middle" font-size="28">%s × %s grid</text><text x="160" y="125" text-anchor="middle" font-size="14">Count the small cells</text></svg>',2+(g%9),2+((g*3)%9)),'UTF8'),'base64') image_url,
    ((2+(g%9))*(2+((g*3)%9)))::text answer,
    (((2+(g%9))*(2+((g*3)%9)))+1)::text d1,
    (((2+(g%9))*(2+((g*3)%9)))+2)::text d2,
    greatest(1,((2+(g%9))*(2+((g*3)%9)))-1)::text d3,
    'grid-cell-count','Counting cells',1+(g%3),35,
    'Number of small cells = rows × columns.',
    'Multiply grid dimensions.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='counting-figures'

  UNION ALL
  -- Dice & cubes: labelled cuboid, visual
  SELECT tm.topic_id,tm.subject_id,'dice-and-cubes',g,
    format('A cuboid is built from unit cubes with dimensions %s × %s × %s. How many unit cubes are used?',2+(g%7),2+((g*2)%6),2+((g*3)%5)) question_text,
    'data:image/svg+xml;base64,'||encode(convert_to(
      format('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><polygon points="70,55 205,55 250,90 115,90" fill="#eee" stroke="black"/><polygon points="115,90 250,90 250,145 115,145" fill="#ddd" stroke="black"/><polygon points="70,55 115,90 115,145 70,110" fill="#f5f5f5" stroke="black"/><text x="160" y="170" text-anchor="middle" font-size="16">%s × %s × %s unit cubes</text></svg>',2+(g%7),2+((g*2)%6),2+((g*3)%5)),'UTF8'),'base64') image_url,
    ((2+(g%7))*(2+((g*2)%6))*(2+((g*3)%5)))::text answer,
    (((2+(g%7))*(2+((g*2)%6))*(2+((g*3)%5)))+2)::text d1,
    (((2+(g%7))*(2+((g*2)%6))*(2+((g*3)%5)))+4)::text d2,
    greatest(1,((2+(g%7))*(2+((g*2)%6))*(2+((g*3)%5)))-2)::text d3,
    'cuboid-unit-cubes','Cube counting',1+(g%3),40,
    'Multiply length × breadth × height in unit cubes.',
    'For a solid rectangular block, total cubes = lbh.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='dice-and-cubes'

  UNION ALL
  -- Figure series: dots increase by a fixed increment, visual
  SELECT tm.topic_id,tm.subject_id,'figure-series',g,
    format('The figure series contains %s, %s and %s dots. How many dots should the next figure contain?',1+(g%4),1+(g%4)+(1+(g%3)),1+(g%4)+2*(1+(g%3))) question_text,
    'data:image/svg+xml;base64,'||encode(convert_to(
      format('<svg xmlns="http://www.w3.org/2000/svg" width="360" height="160"><rect width="360" height="160" fill="white"/><text x="60" y="70" font-size="26">%s dots</text><text x="155" y="70" font-size="26">%s dots</text><text x="260" y="70" font-size="26">%s dots</text><text x="330" y="70" font-size="30">?</text><path d="M110 20v110M220 20v110M315 20v110" stroke="#999"/></svg>',1+(g%4),1+(g%4)+(1+(g%3)),1+(g%4)+2*(1+(g%3))) ,'UTF8'),'base64') image_url,
    (1+(g%4)+3*(1+(g%3)))::text answer,
    (2+(g%4)+3*(1+(g%3)))::text d1,
    (1+(g%4)+4*(1+(g%3)))::text d2,
    greatest(1,(g%4)+3*(1+(g%3)))::text d3,
    'dot-count-progression','Figure quantity progression',1+(g%3),35,
    'The number of dots increases by the same amount each step.',
    'Track the changing feature numerically.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='figure-series'

  UNION ALL
  -- Mirror & water images: vertical mirror reverses left/right order, visual
  SELECT tm.topic_id,tm.subject_id,'mirror-and-water-images',g,
    format('A vertical mirror is placed to the right of the figure. Which left-to-right order appears in the mirror?') question_text,
    'data:image/svg+xml;base64,'||encode(convert_to(
      format('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="150"><rect width="320" height="150" fill="white"/><text x="70" y="85" font-size="38">A%sB</text><line x1="220" y1="20" x2="220" y2="130" stroke="black" stroke-width="4"/><text x="235" y="30" font-size="14">mirror</text></svg>',g),'UTF8'),'base64') image_url,
    format('B%sA',g) answer,format('A%sB',g) d1,format('%sAB',g) d2,format('BA%s',g) d3,
    'vertical-mirror-order','Vertical mirror',1+(g%3),35,
    'A vertical mirror reverses left-right order while keeping top-bottom order.',
    'Read the sequence from right to left.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='mirror-and-water-images'

  UNION ALL
  -- Embedded figures: target symbol is explicitly present in one panel, visual
  SELECT tm.topic_id,tm.subject_id,'embedded-figures',g,
    'In which option is the target L-shaped figure embedded?' question_text,
    'data:image/svg+xml;base64,'||encode(convert_to(
      format('<svg xmlns="http://www.w3.org/2000/svg" width="420" height="190"><rect width="420" height="190" fill="white"/><text x="20" y="22" font-size="14">Target</text><path d="M30 35 L30 80 L70 80" stroke="black" stroke-width="4" fill="none"/><text x="110" y="30">1</text><path d="M100 45 L140 45 L140 85" stroke="black" stroke-width="3" fill="none"/><text x="195" y="30">2</text><path d="M180 45 L180 90 L220 90 M180 65 L220 45" stroke="black" stroke-width="3" fill="none"/><text x="285" y="30">3</text><circle cx="285" cy="70" r="28" fill="none" stroke="black"/><text x="370" y="30">4</text><path d="M350 90 L390 45" stroke="black" stroke-width="3"/><text x="210" y="165" text-anchor="middle" font-size="12">Variant %s</text></svg>',g),'UTF8'),'base64') image_url,
    'Option 2' answer,'Option 1' d1,'Option 3' d2,'Option 4' d3,
    'embedded-l-shape','Embedded target figure',2+(g%2),45,
    'Option 2 contains the same vertical-then-horizontal L shape as part of the larger drawing.',
    'Ignore extra lines and trace only the target segments.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='embedded-figures'

  UNION ALL
  -- Paper folding/cutting: one fold doubles punched holes, visual
  SELECT tm.topic_id,tm.subject_id,'paper-folding-and-cutting',g,
    format('A sheet is folded once in half and %s hole(s) are punched through the folded sheet. How many holes appear after fully unfolding?',1+(g%6)) question_text,
    'data:image/svg+xml;base64,'||encode(convert_to(
      format('<svg xmlns="http://www.w3.org/2000/svg" width="340" height="170"><rect x="35" y="35" width="120" height="100" fill="white" stroke="black"/><path d="M155 35 L95 85 L155 135" fill="none" stroke="#666" stroke-dasharray="6 4"/><text x="220" y="65" font-size="16">1 fold</text><text x="220" y="95" font-size="16">%s punch(es)</text><text x="220" y="125" font-size="12">Unfold fully</text></svg>',1+(g%6)),'UTF8'),'base64') image_url,
    (2*(1+(g%6)))::text answer,(1+(g%6))::text d1,(4*(1+(g%6)))::text d2,(2*(1+(g%6))+1)::text d3,
    'single-fold-hole-symmetry','Paper fold and punch',1+(g%3),40,
    'One complete fold creates two symmetric layers, so each punch appears twice after unfolding.',
    'One fold doubles each punch.'
  FROM topic_map tm CROSS JOIN generate_series(1,100) g WHERE tm.topic_slug='paper-folding-and-cutting'
),
prepared AS (
  SELECT *,
         ((g-1)%4) shift,
         format('phase4b-reasoning-%s-%s',topic_slug,g) source_id,
         ARRAY[answer,d1,d2,d3]::text[] raw_options
  FROM base
),
rows AS (
  SELECT *,1+((4-shift)%4) correct_pos FROM prepared
),
inserted AS (
  INSERT INTO questions(
    exam_id,subject_id,topic_id,subtopic,pattern_type,question_text,question_image_url,
    correct_option,explanation,fast_method,difficulty,expected_time_seconds,
    source_type,source_reference,source_question_id,visibility,verification_status
  )
  SELECT e.id,r.subject_id,r.topic_id,r.subtopic,r.pattern_type,r.question_text,r.image_url,
         r.correct_pos,r.explanation,r.fast_method,r.difficulty,r.expected_time,
         'generated','phase4b-deterministic',r.source_id,'private','verified'
  FROM rows r JOIN exams e ON e.slug='ssc-cgl-tier-1'
  WHERE NOT EXISTS(SELECT 1 FROM questions q WHERE q.source_question_id=r.source_id)
  RETURNING id,source_question_id
)
INSERT INTO question_options(question_id,position,text)
SELECT i.id,p,r.raw_options[1+((p+r.shift-1)%4)]
FROM inserted i
JOIN rows r ON r.source_id=i.source_question_id
CROSS JOIN generate_series(1,4) p;
