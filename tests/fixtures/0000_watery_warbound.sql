CREATE TABLE `prediction_accounts` (
	`id` text PRIMARY KEY NOT NULL,
	`member` text NOT NULL,
	`username` text NOT NULL,
	`salt` text NOT NULL,
	`password_hash` text NOT NULL,
	`role` text NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `prediction_accounts_member_unique` ON `prediction_accounts` (`member`);--> statement-breakpoint
CREATE UNIQUE INDEX `prediction_accounts_username_unique` ON `prediction_accounts` (`username`);--> statement-breakpoint
CREATE TABLE `prediction_invites` (
	`member` text PRIMARY KEY NOT NULL,
	`hash` text NOT NULL,
	`expires` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `prediction_login_limits` (
	`key` text PRIMARY KEY NOT NULL,
	`attempts` integer NOT NULL,
	`expires` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `predictions` (
	`id` text PRIMARY KEY NOT NULL,
	`season` integer NOT NULL,
	`author` text NOT NULL,
	`title` text NOT NULL,
	`criteria` text NOT NULL,
	`mode` text NOT NULL,
	`amount` integer NOT NULL,
	`deadline` integer NOT NULL,
	`resolve_at` integer NOT NULL,
	`outcome` text,
	`note` text DEFAULT '' NOT NULL,
	`version` integer DEFAULT 0 NOT NULL,
	`is_test` integer DEFAULT 0 NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_predictions_season_test` ON `predictions` (`season`,`is_test`);--> statement-breakpoint
CREATE TABLE `prediction_responses` (
	`id` text PRIMARY KEY NOT NULL,
	`prediction_id` text NOT NULL,
	`member` text NOT NULL,
	`decision` text NOT NULL,
	`amount` integer NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`prediction_id`) REFERENCES `predictions`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `idx_prediction_response_member` ON `prediction_responses` (`prediction_id`,`member`);--> statement-breakpoint
CREATE TABLE `prediction_rulings` (
	`id` text PRIMARY KEY NOT NULL,
	`prediction_id` text NOT NULL,
	`commissioner` text NOT NULL,
	`outcome` text NOT NULL,
	`note` text NOT NULL,
	`version` integer NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`prediction_id`) REFERENCES `predictions`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `idx_prediction_rulings_prediction` ON `prediction_rulings` (`prediction_id`);--> statement-breakpoint
CREATE TABLE `prediction_sessions` (
	`hash` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`expires` integer NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `prediction_accounts`(`id`) ON UPDATE no action ON DELETE no action
);
