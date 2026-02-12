-- Allow multiple candidate_articles per run with the same canonical_url but different titles
-- (e.g. one newsletter URL listing several items → one row per item).
-- Drop old unique index, add new one on (run_id, canonical_url, COALESCE(title, '')).

DROP INDEX IF EXISTS ux_candidate_articles_run_canonical;

CREATE UNIQUE INDEX IF NOT EXISTS ux_candidate_articles_run_canonical_title
ON candidate_articles (run_id, canonical_url, COALESCE(title, ''));
