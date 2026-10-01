CREATE TABLE `prediction_seasons` (
	`key` text PRIMARY KEY NOT NULL,
	`season` integer NOT NULL,
	`is_test` integer DEFAULT 0 NOT NULL,
	`closed_at` integer NOT NULL,
	`closed_by` text NOT NULL
);
