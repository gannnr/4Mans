CREATE TABLE prediction_accounts (
	id text PRIMARY KEY NOT NULL,
	member text NOT NULL,
	username text NOT NULL,
	salt text NOT NULL,
	password_hash text NOT NULL,
	role text NOT NULL,
	created_at bigint NOT NULL
);

CREATE UNIQUE INDEX prediction_accounts_member_unique ON prediction_accounts (member);
CREATE UNIQUE INDEX prediction_accounts_username_unique ON prediction_accounts (username);
CREATE TABLE prediction_invites (
	member text PRIMARY KEY NOT NULL,
	hash text NOT NULL,
	expires bigint NOT NULL
);

CREATE TABLE prediction_login_limits (
	key text PRIMARY KEY NOT NULL,
	attempts bigint NOT NULL,
	expires bigint NOT NULL
);

CREATE TABLE predictions (
	id text PRIMARY KEY NOT NULL,
	season bigint NOT NULL,
	author text NOT NULL,
	title text NOT NULL,
	criteria text NOT NULL,
	mode text NOT NULL,
	amount bigint NOT NULL,
	deadline bigint NOT NULL,
	resolve_at bigint NOT NULL,
	outcome text,
	note text DEFAULT '' NOT NULL,
	version bigint DEFAULT 0 NOT NULL,
	is_test bigint DEFAULT 0 NOT NULL,
	created_at bigint NOT NULL
);

CREATE INDEX idx_predictions_season_test ON predictions (season,is_test);
CREATE TABLE prediction_responses (
	id text PRIMARY KEY NOT NULL,
	prediction_id text NOT NULL,
	member text NOT NULL,
	decision text NOT NULL,
	amount bigint NOT NULL,
	created_at bigint NOT NULL,
	FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON UPDATE no action ON DELETE no action
);

CREATE UNIQUE INDEX idx_prediction_response_member ON prediction_responses (prediction_id,member);
CREATE TABLE prediction_rulings (
	id text PRIMARY KEY NOT NULL,
	prediction_id text NOT NULL,
	commissioner text NOT NULL,
	outcome text NOT NULL,
	note text NOT NULL,
	version bigint NOT NULL,
	created_at bigint NOT NULL,
	FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON UPDATE no action ON DELETE no action
);

CREATE INDEX idx_prediction_rulings_prediction ON prediction_rulings (prediction_id);
CREATE TABLE prediction_sessions (
	hash text PRIMARY KEY NOT NULL,
	account_id text NOT NULL,
	expires bigint NOT NULL,
	FOREIGN KEY (account_id) REFERENCES prediction_accounts(id) ON UPDATE no action ON DELETE no action
);

CREATE TABLE prediction_seasons (
	key text PRIMARY KEY NOT NULL,
	season bigint NOT NULL,
	is_test bigint DEFAULT 0 NOT NULL,
	closed_at bigint NOT NULL,
	closed_by text NOT NULL
);

ALTER TABLE public.prediction_accounts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.prediction_accounts FROM anon, authenticated;
GRANT ALL ON public.prediction_accounts TO service_role;

ALTER TABLE public.prediction_invites ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.prediction_invites FROM anon, authenticated;
GRANT ALL ON public.prediction_invites TO service_role;

ALTER TABLE public.prediction_login_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.prediction_login_limits FROM anon, authenticated;
GRANT ALL ON public.prediction_login_limits TO service_role;

ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.predictions FROM anon, authenticated;
GRANT ALL ON public.predictions TO service_role;

ALTER TABLE public.prediction_responses ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.prediction_responses FROM anon, authenticated;
GRANT ALL ON public.prediction_responses TO service_role;

ALTER TABLE public.prediction_rulings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.prediction_rulings FROM anon, authenticated;
GRANT ALL ON public.prediction_rulings TO service_role;

ALTER TABLE public.prediction_sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.prediction_sessions FROM anon, authenticated;
GRANT ALL ON public.prediction_sessions TO service_role;

ALTER TABLE public.prediction_seasons ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.prediction_seasons FROM anon, authenticated;
GRANT ALL ON public.prediction_seasons TO service_role;

CREATE OR REPLACE FUNCTION public.fourmans_transaction(statements jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp AS $$
DECLARE s jsonb; q text; chunks text[]; i integer; val text; result jsonb; output jsonb='[]'; changed bigint;
BEGIN
 IF current_user <> 'service_role' THEN RAISE EXCEPTION 'Server access required'; END IF;
 IF jsonb_typeof(statements)<>'array' OR jsonb_array_length(statements)>20 THEN RAISE EXCEPTION 'Invalid batch'; END IF;
 PERFORM pg_advisory_xact_lock(4466262026);
 FOR s IN SELECT value FROM jsonb_array_elements(statements) LOOP
  chunks=string_to_array(s->>'sql','?');q=chunks[1];
  IF coalesce(jsonb_array_length(s->'params'),0)<>array_length(chunks,1)-1 THEN RAISE EXCEPTION 'Invalid parameters'; END IF;
  FOR i IN 2..array_length(chunks,1) LOOP
   val=s->'params'->>(i-2);q=q||quote_nullable(val)||chunks[i];
  END LOOP;
  IF q !~ '^(SELECT|INSERT|UPDATE|DELETE) ' THEN RAISE EXCEPTION 'Invalid statement'; END IF;
  IF s->>'mode'='select' THEN
   EXECUTE 'SELECT coalesce(jsonb_agg(to_jsonb(t)),''[]''::jsonb) FROM ('||q||') t' INTO result;
   output=output||jsonb_build_array(jsonb_build_object('results',result));
  ELSE
   EXECUTE q;GET DIAGNOSTICS changed=ROW_COUNT;
   output=output||jsonb_build_array(jsonb_build_object('meta',jsonb_build_object('changes',changed)));
  END IF;
 END LOOP;
 RETURN output;
END;$$;
REVOKE ALL ON FUNCTION public.fourmans_transaction(jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.fourmans_transaction(jsonb) TO service_role;
