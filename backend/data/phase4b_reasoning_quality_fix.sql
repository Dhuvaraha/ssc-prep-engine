-- Phase 4B deterministic quality repair for reasoning seed.
-- Keeps correct answers intact while replacing collided distractors and expanding
-- Figure Series, Counting Figures, and Paper Folding/Cutting to 100 distinct prompts.

-- Dictionary order
WITH q AS (
  SELECT id, regexp_replace(source_question_id, '^.*-', '')::int AS g
  FROM questions
  WHERE source_question_id LIKE 'phase4b-reasoning-dictionary-order-%'
), words AS (
  SELECT q.*,
         ARRAY[
           chr(97+(g%20))||'able'||chr(97+((g+3)%26)),
           chr(97+(g%20))||'able'||chr(97+((g+8)%26)),
           chr(97+(g%20))||'able'||chr(97+((g+13)%26)),
           chr(97+(g%20))||'able'||chr(97+((g+18)%26))
         ]::text[] AS candidates,
         ((g-1)%4) AS shift
  FROM q
), prepared AS (
  SELECT *,least(candidates[1],candidates[2],candidates[3],candidates[4]) AS answer FROM words
), options AS (
  SELECT *,ARRAY[answer] || ARRAY(SELECT w FROM unnest(candidates) w WHERE w<>answer ORDER BY w) AS raw_options
  FROM prepared
)
UPDATE question_options o
SET text=x.raw_options[1+((o.position+x.shift-1)%4)]
FROM options x WHERE o.question_id=x.id;

-- Figure series
WITH q AS (
  SELECT id,regexp_replace(source_question_id,'^.*-','')::int g
  FROM questions WHERE source_question_id LIKE 'phase4b-reasoning-figure-series-%'
), p AS (
  SELECT *,g+1 start_value,1+(g%5) step,((g-1)%4) shift FROM q
), u AS (
  UPDATE questions z
  SET question_text=format('The figure series contains %s, %s and %s dots. How many dots should the next figure contain?',p.start_value,p.start_value+p.step,p.start_value+2*p.step),
      question_image_url='data:image/svg+xml;base64,'||encode(convert_to(format('<svg xmlns="http://www.w3.org/2000/svg" width="380" height="160"><rect width="380" height="160" fill="white"/><text x="55" y="70" font-size="24">%s dots</text><text x="155" y="70" font-size="24">%s dots</text><text x="265" y="70" font-size="24">%s dots</text><text x="350" y="70" font-size="28">?</text><path d="M110 20v110M220 20v110M325 20v110" stroke="#999"/></svg>',p.start_value,p.start_value+p.step,p.start_value+2*p.step),'UTF8'),'base64'),
      explanation=format('The number of dots increases by %s each step, so the next count is %s.',p.step,p.start_value+3*p.step),
      fast_method='Track the changing feature numerically.'
  FROM p WHERE z.id=p.id RETURNING z.id
)
UPDATE question_options o
SET text=a.raw_options[1+((o.position+a.shift-1)%4)]
FROM (
  SELECT p.id,p.shift,ARRAY[(p.start_value+3*p.step)::text,(p.start_value+3*p.step+1)::text,(p.start_value+3*p.step+2)::text,greatest(1,p.start_value+3*p.step-1)::text]::text[] raw_options
  FROM p
) a WHERE o.question_id=a.id;

-- Counting figures
WITH q AS (
  SELECT id,regexp_replace(source_question_id,'^.*-','')::int g
  FROM questions WHERE source_question_id LIKE 'phase4b-reasoning-counting-figures-%'
), p AS (
  SELECT *,2+((g-1)%10) rows_n,2+floor((g-1)/10.0)::int cols_n,((g-1)%4) shift FROM q
), u AS (
  UPDATE questions z
  SET question_text=format('How many small cells are present in this %s × %s grid?',p.rows_n,p.cols_n),
      question_image_url='data:image/svg+xml;base64,'||encode(convert_to(format('<svg xmlns="http://www.w3.org/2000/svg" width="360" height="220"><defs><pattern id="cell" width="20" height="15" patternUnits="userSpaceOnUse"><rect width="20" height="15" fill="white" stroke="black" stroke-width="1"/></pattern></defs><rect x="30" y="25" width="%s" height="%s" fill="url(#cell)" stroke="black"/><text x="180" y="205" text-anchor="middle" font-size="14">%s rows × %s columns</text></svg>',p.cols_n*20,p.rows_n*15,p.rows_n,p.cols_n),'UTF8'),'base64'),
      explanation=format('There are %s rows and %s columns, so cells = %s × %s = %s.',p.rows_n,p.cols_n,p.rows_n,p.cols_n,p.rows_n*p.cols_n),
      fast_method='Multiply rows by columns.'
  FROM p WHERE z.id=p.id RETURNING z.id
)
UPDATE question_options o
SET text=a.raw_options[1+((o.position+a.shift-1)%4)]
FROM (
  SELECT p.id,p.shift,ARRAY[(p.rows_n*p.cols_n)::text,(p.rows_n*p.cols_n+1)::text,(p.rows_n*p.cols_n+2)::text,greatest(1,p.rows_n*p.cols_n-1)::text]::text[] raw_options
  FROM p
) a WHERE o.question_id=a.id;

-- Paper folding and cutting
WITH q AS (
  SELECT id,regexp_replace(source_question_id,'^.*-','')::int g
  FROM questions WHERE source_question_id LIKE 'phase4b-reasoning-paper-folding-and-cutting-%'
), p AS (
  SELECT *,1+((g-1)%3) folds_n,1+floor((g-1)/3.0)::int punches_n,((g-1)%4) shift FROM q
), u AS (
  UPDATE questions z
  SET question_text=format('A sheet is folded %s time(s) in half. Then %s hole(s), away from fold lines, are punched through all layers. How many holes appear after fully unfolding?',p.folds_n,p.punches_n),
      question_image_url='data:image/svg+xml;base64,'||encode(convert_to(format('<svg xmlns="http://www.w3.org/2000/svg" width="360" height="180"><rect x="35" y="30" width="130" height="110" fill="white" stroke="black"/><path d="M165 30 L100 85 L165 140" fill="none" stroke="#666" stroke-dasharray="6 4"/><text x="235" y="65" font-size="17">%s fold(s)</text><text x="235" y="95" font-size="17">%s punch(es)</text><text x="235" y="125" font-size="12">away from creases</text></svg>',p.folds_n,p.punches_n),'UTF8'),'base64'),
      explanation=format('%s fold(s) create %s layers. Each of %s punches is copied to every layer, giving %s holes.',p.folds_n,power(2,p.folds_n)::int,p.punches_n,p.punches_n*power(2,p.folds_n)::int),
      fast_method='Each clean half-fold doubles the number of symmetric copies.'
  FROM p WHERE z.id=p.id RETURNING z.id
)
UPDATE question_options o
SET text=a.raw_options[1+((o.position+a.shift-1)%4)]
FROM (
  SELECT p.id,p.shift,ARRAY[(p.punches_n*power(2,p.folds_n)::int)::text,(p.punches_n*power(2,p.folds_n)::int+1)::text,(p.punches_n*power(2,p.folds_n)::int+2)::text,greatest(1,p.punches_n*power(2,p.folds_n)::int-1)::text]::text[] raw_options
  FROM p
) a WHERE o.question_id=a.id;
